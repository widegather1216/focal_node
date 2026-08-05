import os
import sys
import time

sys.path.insert(0, os.path.abspath("backend/app"))
sys.path.insert(0, os.path.abspath("backend"))

import torch
from services.unipercept_adapter import get_unipercept_adapter, build_transform, GPU_LOCK
from PIL import Image, ImageOps

def score2aestoken(n):
    if not (0 <= n <= 100):
        raise ValueError("Score must be between 0 and 100 inclusive.")
    if 0 <= n <= 25:
        first = 'a'
        offset = n
    elif 26 <= n <= 50:
        first = 'c'
        offset = n - 26
    elif 51 <= n <= 75:
        first = 'd'
        offset = n - 51
    else:
        first = 'e'
        offset = n - 76
    second = chr(ord('a') + offset)
    return first + second

AESTHETICS_TOKEN_LIST = [score2aestoken(i) for i in range(101)]

def compute_official_vr_score(adapter, pixel_values, desc: str):
    tokenizer = adapter.tokenizer
    model = adapter.model
    device = adapter.device
    
    question = (
        f"<image>Rate the {desc} score of the image in 0-100. "
        f"In the output format, numbers are replaced by 2 corresponding letters, and the mapping relationship is: "
        f"score 0 to 25: 0-aa, 1-ab, 2-ac, 3-ad, ... , 25-az, \n"
        f"score 26 to 50: 26-ca, 27-cb, 28-cc, 29-cd, ..., 50-cy, \n"
        f"score 51 to 75: 51-da, 52-db, 53-dc, 54-dd, ..., 75-dy, \n"
        f"score 76 to 100: 76-ea, 77-eb, 73-ec, 74-ed, ..., 100-ey. \n"
        f"The answer only outputs 2 corresponding letters."
    )
    
    IMG_START_TOKEN = '<img>'
    IMG_END_TOKEN = '</img>'
    IMG_CONTEXT_TOKEN = '<IMG_CONTEXT>'
    
    # We can use model.score or manual logit extraction:
    if hasattr(model, "score"):
        gen_cfg = dict(max_new_tokens=512, do_sample=False)
        with GPU_LOCK:
            return model.score(device, tokenizer, pixel_values, gen_cfg, desc)
    else:
        # Import conversation template from the model snapshot directory or transformers
        import importlib.util
        snapshot_dir = "/Users/kimbeomjun/.cache/huggingface/hub/models--widegather--unipercept-mirror/snapshots/0eda09ec33ee0fca5131965828bf86c175581a66"
        conv_path = os.path.join(snapshot_dir, "conversation.py")
        spec = importlib.util.spec_from_file_location("conversation", conv_path)
        conv_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(conv_mod)
        get_conv_template = conv_mod.get_conv_template

        template_name = getattr(model.config, 'template', 'internvl2_5') if hasattr(model, 'config') else 'internvl2_5'
        template = get_conv_template(template_name)
        template.system_message = getattr(model.config, 'system_message', '') if hasattr(model, 'config') else ''
        template.append_message(template.roles[0], question)
        template.append_message(template.roles[1], None)
        query = template.get_prompt()
        
        img_context_token_id = tokenizer.convert_tokens_to_ids(IMG_CONTEXT_TOKEN)
        num_patches = pixel_values.shape[0] if pixel_values is not None else 1
        num_image_token = getattr(model, 'num_image_token', 256)
        image_tokens = IMG_START_TOKEN + IMG_CONTEXT_TOKEN * num_image_token * num_patches + IMG_END_TOKEN
        query = query.replace('<image>', image_tokens, 1)
        
        model_inputs = tokenizer(query, return_tensors='pt')
        input_ids = model_inputs['input_ids'].to(device)
        attention_mask = model_inputs['attention_mask'].to(device)
        
        with GPU_LOCK:
            with torch.no_grad():
                vit_embeds = model.extract_feature(pixel_values)
                input_embeds = model.language_model.get_input_embeddings()(input_ids)
                B, N, C = input_embeds.shape
                input_embeds = input_embeds.reshape(B * N, C)
                input_ids_flat = input_ids.reshape(B * N)
                selected = (input_ids_flat == img_context_token_id)
                input_embeds[selected] = vit_embeds.reshape(-1, C).to(input_embeds.device)
                input_embeds = input_embeds.reshape(B, N, C)
                
                outputs = model.language_model(
                    inputs_embeds=input_embeds,
                    attention_mask=attention_mask,
                    use_cache=True,
                    output_hidden_states=True,
                    return_dict=True,
                )
                logits = outputs.logits
        
        preferential_ids_ = [tokenizer.convert_tokens_to_ids(word) for word in AESTHETICS_TOKEN_LIST]
        output_logits = logits[:, -1, preferential_ids_].detach()
        weight_tensor = torch.tensor([x for x in range(101)]).to(device=device, dtype=output_logits.dtype)
        score = torch.softmax(output_logits, -1) @ weight_tensor
        return score.item()

def main():
    img_path = os.path.abspath("scratch/test_images/test_scenic.jpg")
    adapter = get_unipercept_adapter()
    adapter._load_model_locked()
    
    with Image.open(img_path) as raw_img:
        t_img = ImageOps.exif_transpose(raw_img)
        pil_img = t_img.convert("RGB") if t_img.mode != "RGB" else t_img.copy()

    target_dtype = adapter.torch_dtype
    if adapter.model is not None and hasattr(adapter.model, "parameters"):
        try:
            target_dtype = next(adapter.model.parameters()).dtype
        except Exception:
            pass

    transform = build_transform(input_size=448)
    pixel_values = transform(pil_img).unsqueeze(0).to(dtype=target_dtype).to(adapter.device)

    print("=== Testing 100% Official UniPercept VR Scoring (3 Calls) ===")
    
    domains = {
        "iaa": "aesthetics",
        "iqa": "quality",
        "ista": "structure and texture richness"
    }
    
    scores = {}
    for key, desc in domains.items():
        t0 = time.time()
        score = compute_official_vr_score(adapter, pixel_values, desc)
        elapsed = time.time() - t0
        scores[key] = score
        print(f"[{key.upper()}] Official VR Score: {score:.2f}/100 (Time: {elapsed:.2f}s)")
    
    overall = round(0.4 * scores['iaa'] + 0.3 * scores['iqa'] + 0.3 * scores['ista'])
    print(f"\nCalculated Overall Score: {overall}/100")
    
    adapter.unload_model()

if __name__ == "__main__":
    main()
