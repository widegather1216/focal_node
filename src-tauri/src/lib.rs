use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio, Child};
use std::sync::{Arc, Mutex, Condvar};
use std::thread;
use regex::Regex;
use tauri::{Manager, Emitter};

fn resolve_dev_sidecar_command() -> (String, Vec<String>) {
    let current_dir = std::env::current_dir().unwrap_or_default();
    let mut script_path = current_dir.join("backend/app/main.py");
    let mut venv_python_path = None;

    for prefix in &["", "../", "../../"] {
        let candidate_script = current_dir.join(prefix).join("backend/app/main.py");
        if !candidate_script.exists() {
            continue;
        }
        script_path = candidate_script;
        let venv_dir = current_dir.join(prefix).join("venv");
        let py_exe = if cfg!(target_os = "windows") {
            venv_dir.join("Scripts").join("python.exe")
        } else {
            venv_dir.join("bin").join("python3")
        };
        if py_exe.exists() {
            venv_python_path = Some(py_exe);
        }
        break;
    }

    let py_program = match venv_python_path {
        Some(p) => p.to_string_lossy().to_string(),
        None => "python3".to_string(),
    };
    (py_program, vec![script_path.to_string_lossy().to_string()])
}

fn resolve_release_sidecar_path(resource_dir: Option<&Path>, exe_path: &Path) -> Result<PathBuf, String> {
    #[cfg(target_os = "macos")]
    {
        let mut candidates: Vec<PathBuf> = Vec::new();
        if let Some(res_dir) = resource_dir {
            candidates.push(res_dir.join("binaries").join("focal_node_backend"));
        }
        if let Some(contents_dir) = exe_path.parent().and_then(|macos| macos.parent()) {
            candidates.push(contents_dir.join("Resources").join("binaries").join("focal_node_backend"));
        }
        if let Some(exe_dir) = exe_path.parent() {
            candidates.push(exe_dir.join("focal_node_backend"));
        }
        for candidate in &candidates {
            if candidate.is_file() {
                return Ok(candidate.clone());
            }
        }
        return Err(format!("Backend sidecar binary not found. Checked: {:?}", candidates));
    }

    #[cfg(not(target_os = "macos"))]
    {
        let _ = resource_dir;
        let sidecar_name = if cfg!(target_os = "windows") {
            "focal_node_backend.exe"
        } else {
            "focal_node_backend"
        };
        let parent_dir = exe_path
            .parent()
            .ok_or_else(|| format!("Failed to resolve executable parent directory for {:?}", exe_path))?;
        Ok(parent_dir.join(sidecar_name))
    }
}

fn notify_sidecar_error(state: &AppState, err_msg: String) {
    eprintln!("[Tauri Rust] {}", err_msg);
    if let Ok(mut err_guard) = state.error.lock() {
        *err_guard = Some(err_msg);
    }
    let _port_guard = state.port.lock();
    state.condvar.notify_all();
}

pub struct AppState {
    port: Mutex<Option<u16>>,
    error: Mutex<Option<String>>,
    condvar: Condvar,
    child: Mutex<Option<Child>>,
}

#[tauri::command]
async fn get_api_port(state: tauri::State<'_, Arc<AppState>>) -> Result<u16, String> {
    loop {
        {
            let port_guard = state.port.lock().map_err(|e| e.to_string())?;
            if let Some(port) = *port_guard {
                return Ok(port);
            }
            let err_guard = state.error.lock().map_err(|e| e.to_string())?;
            if let Some(ref err_msg) = *err_guard {
                return Err(err_msg.clone());
            }
        }
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    }
}

#[tauri::command]
fn reveal_in_finder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg("-R")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg("/select,")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "linux")]
    {
        // Linux doesn't have a direct equivalent to select a file in a file manager universally,
        // so we just open the directory containing the file or the file itself.
        Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

const BLOCKED_EXPORT_SYSTEM_PREFIXES: &[&str] = &[
    "/System",
    "/Library",
    "/usr",
    "/bin",
    "/sbin",
    "/etc",
    "/private/etc",
    "/dev",
    "/cores",
    "/Applications",
    "/private/var/root",
    "/private/var/db",
    "/private/var/log",
];

fn validate_export_raw_input(raw_path: &str) -> Result<&Path, String> {
    if raw_path.trim().is_empty() {
        return Err("Export path must not be empty.".to_string());
    }
    if raw_path.contains('\0') {
        return Err("Export path must not contain NUL bytes.".to_string());
    }
    if raw_path.ends_with('/') || raw_path.ends_with(std::path::MAIN_SEPARATOR) || raw_path.ends_with("/.") {
        return Err("Export path must refer to a file, not a directory.".to_string());
    }
    let input_path = Path::new(raw_path);
    if !input_path.is_absolute() {
        return Err("Export path must be an absolute path.".to_string());
    }
    let has_traversal = input_path.components().any(|component| {
        matches!(component, std::path::Component::ParentDir | std::path::Component::CurDir)
    });
    if has_traversal {
        return Err("Export path must not contain relative traversal segments.".to_string());
    }
    Ok(input_path)
}

fn validate_export_filename(input_path: &Path) -> Result<&str, String> {
    let file_name = input_path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| "Export path must contain a valid UTF-8 file name.".to_string())?;
    if file_name.starts_with('.') {
        return Err("Hidden dotfiles are not allowed for export.".to_string());
    }
    let extension = input_path
        .extension()
        .and_then(|ext| ext.to_str())
        .map(|ext| ext.to_ascii_lowercase());
    if !matches!(extension.as_deref(), Some("pdf") | Some("md")) {
        return Err("Only .pdf and .md export files are allowed.".to_string());
    }
    Ok(file_name)
}

fn is_blocked_system_dir(canonical_parent: &Path) -> bool {
    if canonical_parent == Path::new("/") {
        return true;
    }
    if BLOCKED_EXPORT_SYSTEM_PREFIXES.iter().any(|prefix| canonical_parent.starts_with(prefix)) {
        return true;
    }
    canonical_parent.components().any(|component| match component {
        std::path::Component::Normal(segment) => {
            segment.to_string_lossy().to_ascii_lowercase().ends_with(".app")
        }
        _ => false,
    })
}

fn ensure_safe_export_target(target_path: &Path) -> Result<(), String> {
    match std::fs::symlink_metadata(target_path) {
        Ok(metadata) => {
            if metadata.file_type().is_symlink() || !metadata.is_file() {
                return Err("Refusing to write to a symbolic link or non-regular file target.".to_string());
            }
            Ok(())
        }
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(err) => Err(format!("Failed to inspect export target '{}': {}", target_path.display(), err)),
    }
}

fn validate_export_save_path(raw_path: &str) -> Result<PathBuf, String> {
    let input_path = validate_export_raw_input(raw_path)?;
    let file_name = validate_export_filename(input_path)?;
    let parent_dir = input_path
        .parent()
        .ok_or_else(|| "Export path must have a valid parent directory.".to_string())?;
    let canonical_parent = std::fs::canonicalize(parent_dir)
        .map_err(|err| format!("Export parent directory is inaccessible: {}", err))?;
    if !canonical_parent.is_dir() {
        return Err("Export parent path is not a directory.".to_string());
    }
    if is_blocked_system_dir(&canonical_parent) {
        return Err(format!("Refusing to export into protected system directory '{}'.", canonical_parent.display()));
    }
    let target_path = canonical_parent.join(file_name);
    ensure_safe_export_target(&target_path)?;
    Ok(target_path)
}

#[tauri::command]
fn save_binary_file(path: String, data: Vec<u8>) -> Result<(), String> {
    let validated_path = validate_export_save_path(&path)?;
    std::fs::write(&validated_path, &data)
        .map_err(|err| format!("Failed to write file at '{}': {}", validated_path.display(), err))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let state = Arc::new(AppState {
        port: Mutex::new(None),
        error: Mutex::new(None),
        condvar: Condvar::new(),
        child: Mutex::new(None),
    });

    let state_clone = state.clone();

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(state.clone())
        .invoke_handler(tauri::generate_handler![get_api_port, reveal_in_finder, save_binary_file])
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state_for_thread = state_clone.clone();

            thread::spawn(move || {
                // 개발 환경인 경우 backend/app/main.py 기동
                // 릴리즈 환경인 경우 sidecar 바이너리 기동
                let (program, args) = if cfg!(debug_assertions) {
                    resolve_dev_sidecar_command()
                } else {
                    let exe_path = match std::env::current_exe() {
                        Ok(path) => path,
                        Err(err) => {
                            notify_sidecar_error(&state_for_thread, format!("Failed to resolve current executable: {}", err));
                            return;
                        }
                    };
                    let resource_dir = app_handle.path().resource_dir().ok();
                    match resolve_release_sidecar_path(resource_dir.as_deref(), &exe_path) {
                        Ok(sidecar_path) => (sidecar_path.to_string_lossy().to_string(), vec![]),
                        Err(err_msg) => {
                            notify_sidecar_error(&state_for_thread, err_msg);
                            return;
                        }
                    }
                };

                println!("[Tauri Rust] Spawning backend: {} {:?}", program, args);

                let mut cmd = Command::new(&program);
                cmd.args(&args);
                cmd.stdout(Stdio::piped());
                cmd.stderr(Stdio::piped());

                let mut child = match cmd.spawn() {
                    Ok(c) => c,
                    Err(e) => {
                        notify_sidecar_error(&state_for_thread, format!("Failed to spawn backend process: {}", e));
                        return;
                    }
                };

                let stdout = child.stdout.take();
                let stderr = child.stderr.take();

                // 자식 프로세스 핸들 저장
                {
                    let mut child_guard = state_for_thread.child.lock().unwrap();
                    *child_guard = Some(child);
                }

                // stderr 스트리밍 스레드 기동
                if let Some(stderr) = stderr {
                    let app_handle_err = app_handle.clone();
                    thread::spawn(move || {
                        use std::io::Read;
                        let mut reader = BufReader::new(stderr);
                        let mut buf = [0; 1024];
                        let mut current_line = String::new();
                        let re_progress = Regex::new(r"(\d+)%\|").unwrap();
                        
                        
                        
                        loop {
                            match reader.read(&mut buf) {
                                Ok(0) => break, // EOF
                                Ok(n) => {
                                    let chunk = String::from_utf8_lossy(&buf[..n]);
                                    for c in chunk.chars() {
                                        if c == '\n' || c == '\r' {
                                            if !current_line.is_empty() {
                                                if let Some(caps) = re_progress.captures(&current_line) {
                                                    if let Some(pct) = caps.get(1) {
                                                        if let Ok(p) = pct.as_str().parse::<u32>() {
                                                            let _ = app_handle_err.emit("model-download-progress", p);
                                                        }
                                                    }
                                                } else {
                                                    eprintln!("[Backend stderr] {}", current_line);
                                                }
                                                current_line.clear();
                                            }
                                        } else {
                                            current_line.push(c);
                                        }
                                    }
                                }
                                Err(_) => break,
                            }
                        }
                        if !current_line.is_empty() {
                            eprintln!("[Backend stderr] {}", current_line);
                        }
                    });
                }

                // stdout 실시간 스트리밍 & 포트 파싱
                let mut port_detected = false;
                if let Some(stdout) = stdout {
                    #[derive(Clone, serde::Serialize)]
                    struct IndexingProgress {
                        processed: u32,
                        total: u32,
                        file_path: String,
                    }
                    #[derive(Clone, serde::Serialize)]
                    struct IndexingErrorPayload {
                        run_id: u64,
                        message: String,
                    }

                    let reader = BufReader::new(stdout);
                    let re_port = Regex::new(r"\[Sidecar\] PORT:\s*(\d+)").unwrap();
                    let re_indexing = Regex::new(r"\[Indexing\] Progress:\s*(\d+)/(\d+)\s*-\s*(.*)").unwrap();
                    let re_indexing_start = Regex::new(r"\[Indexer\] Starting background indexing\. Found\s*(\d+)\s*files\.").unwrap();
                    let re_indexing_error = Regex::new(r"\[Indexer\] Background indexing failed \[run=(\d+)\]:\s*(.*)").unwrap();
                    
                    for line in reader.lines() {
                        if let Ok(line_str) = line {
                            println!("[Backend stdout] {}", line_str);
                            if let Some(caps) = re_port.captures(&line_str) {
                                if let Some(port_match) = caps.get(1) {
                                    if let Ok(port_num) = port_match.as_str().parse::<u16>() {
                                        let mut port_guard = state_for_thread.port.lock().unwrap();
                                        *port_guard = Some(port_num);
                                        port_detected = true;
                                        state_for_thread.condvar.notify_all();
                                        println!("[Tauri Rust] Port recognized & state notified: {}", port_num);
                                    }
                                }
                            } else if let Some(caps) = re_indexing.captures(&line_str) {
                                if let (Some(processed), Some(total), Some(file_path)) = (caps.get(1), caps.get(2), caps.get(3)) {
                                    if let (Ok(p), Ok(t)) = (processed.as_str().parse::<u32>(), total.as_str().parse::<u32>()) {
                                        let payload = IndexingProgress {
                                            processed: p,
                                            total: t,
                                            file_path: file_path.as_str().to_string(),
                                        };
                                        let _ = app_handle.emit("indexing-progress", payload);
                                    }
                                }
                            } else if let Some(caps) = re_indexing_start.captures(&line_str) {
                                if let Some(total) = caps.get(1) {
                                    if let Ok(t) = total.as_str().parse::<u32>() {
                                        let payload = IndexingProgress {
                                            processed: 0,
                                            total: t,
                                            file_path: "Starting AI analysis...".to_string(),
                                        };
                                        let _ = app_handle.emit("indexing-progress", payload);
                                    }
                                }
                            } else if line_str.contains("[Downloader] Downloading ") {
                                let parts: Vec<&str> = line_str.splitn(2, "[Downloader] Downloading ").collect();
                                if parts.len() == 2 {
                                    let model_name = parts[1].trim().to_string();
                                    let _ = app_handle.emit("model-download-started", model_name);
                                }
                            } else if line_str.contains("[Downloader] Completed all model downloads.") {
                                let _ = app_handle.emit("model-download-completed", ());
                            } else if let Some(caps) = re_indexing_error.captures(&line_str) {
                                let run_id = caps
                                    .get(1)
                                    .and_then(|m| m.as_str().parse::<u64>().ok())
                                    .unwrap_or(0);
                                let message = caps
                                    .get(2)
                                    .map(|m| m.as_str().trim().to_string())
                                    .filter(|s| !s.is_empty())
                                    .unwrap_or_else(|| "인덱싱 처리 중 오류가 발생했습니다.".to_string());
                                let _ = app_handle.emit("indexing-error", IndexingErrorPayload { run_id, message });
                            } else if line_str.contains("[Indexer] Background indexing completed.") {
                                let _ = app_handle.emit("indexing-completed", ());
                            } else if line_str.contains("[Indexer] Background indexing paused.") {
                                let _ = app_handle.emit("indexing-paused", ());
                            } else if line_str.contains("[Indexer] Background indexing resumed.") {
                                let _ = app_handle.emit("indexing-resumed", ());
                            } else if line_str.contains("[Indexer] Background indexing cancelled.") {
                                let _ = app_handle.emit("indexing-cancelled", ());
                            } else if line_str.contains("[Indexer] Sync completed.") {
                                let _ = app_handle.emit("sync-completed", ());
                            }
                        }
                    }
                }

                // 포트 감지에 실패하고 루프가 끝난 경우 (프로세스 조기 종료 혹은 기동 실패)
                if !port_detected {
                    let err_msg = "Backend sidecar terminated or failed to bind to a dynamic port.".to_string();
                    {
                        let mut err_guard = state_for_thread.error.lock().unwrap();
                        *err_guard = Some(err_msg);
                    }
                    let _port_guard = state_for_thread.port.lock().unwrap();
                    state_for_thread.condvar.notify_all();
                    println!("[Tauri Rust] Port detection failed. Error state notified.");
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(move |app_handle, event| {
        match event {
            tauri::RunEvent::WindowEvent {
                event: tauri::WindowEvent::Destroyed,
                ..
            } => {
                // macOS에서는 기본적으로 창을 닫아도 앱이 종료되지 않지만,
                // 백엔드 프로세스가 계속 살아있는 문제를 해결하기 위해 창이 닫히면 앱을 종료합니다.
                let windows = app_handle.webview_windows();
                if windows.is_empty() {
                    println!("[Tauri Rust] All windows closed. Exiting app to kill backend...");
                    app_handle.exit(0);
                }
            }
            tauri::RunEvent::Exit => {
                let state = app_handle.state::<Arc<AppState>>();
                let mut child_guard = state.child.lock().unwrap();
                if let Some(mut child) = child_guard.take() {
                    println!("[Tauri Rust] Killing backend process...");
                    let _ = child.kill();
                    let _ = child.wait(); // 좀비 프로세스 방지를 위한 회수(Reap) 추가
                }
            }
            _ => {}
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn test_backend_spawn_and_port_detection() {
        let state = Arc::new(AppState {
            port: Mutex::new(None),
            error: Mutex::new(None),
            condvar: Condvar::new(),
            child: Mutex::new(None),
        });

        let state_clone = state.clone();
        
        thread::spawn(move || {
            let current_dir = std::env::current_dir().unwrap_or_default();
            let mut script_path = current_dir.join("backend/app/main.py");
            let mut python_path = current_dir.join("venv/bin/python3");
            
            for prefix in &["", "../", "../../"] {
                let s_path = current_dir.join(prefix).join("backend/app/main.py");
                if s_path.exists() {
                    script_path = s_path;
                }
                
                let p_path = current_dir.join(prefix).join("venv/bin/python3");
                if p_path.exists() {
                    python_path = p_path;
                }
            }

            println!("[Test] Spawning python in test: {} {:?}", python_path.display(), script_path.display());

            let mut cmd = Command::new(python_path);
            cmd.arg(script_path);
            cmd.stdout(Stdio::piped());
            cmd.stderr(Stdio::piped());

            let mut child = cmd.spawn().expect("Failed to spawn backend python process in test");
            let stdout = child.stdout.take().unwrap();
            
            {
                *state_clone.child.lock().unwrap() = Some(child);
            }

            let reader = BufReader::new(stdout);
            let re = Regex::new(r"\[Sidecar\] PORT:\s*(\d+)").unwrap();
            for line in reader.lines() {
                if let Ok(line_str) = line {
                    println!("[Test Backend stdout] {}", line_str);
                    if let Some(caps) = re.captures(&line_str) {
                        if let Some(port_match) = caps.get(1) {
                            if let Ok(port_num) = port_match.as_str().parse::<u16>() {
                                let mut port_guard = state_clone.port.lock().unwrap();
                                *port_guard = Some(port_num);
                                state_clone.condvar.notify_all();
                                break;
                            }
                        }
                    }
                }
            }
        });

        // 15초 타임아웃 대기 설정
        let mut port_guard = state.port.lock().unwrap();
        let timeout = Duration::from_secs(15);
        let mut result = Ok(());
        
        while port_guard.is_none() && result.is_ok() {
            let wait_result = state.condvar.wait_timeout(port_guard, timeout).unwrap();
            port_guard = wait_result.0;
            if wait_result.1.timed_out() {
                result = Err("Timed out waiting for backend port in unit test");
            }
        }

        assert!(result.is_ok(), "Test timed out waiting for backend port. Backend may have failed to boot.");
        let port_num = port_guard.unwrap();
        assert!(port_num > 0, "Port must be positive integer");
        println!("[Test] Backend port detected successfully: {}", port_num);

        // API 헬스 체크 통신 검증 시뮬레이션
        let client = reqwest_like_fetch(port_num);
        assert!(client.is_ok(), "Failed to fetch backend health status");
        println!("[Test] Backend health api responded with: {:?}", client.unwrap());

        // 자식 프로세스 정리 및 좀비 회수
        let mut child_guard = state.child.lock().unwrap();
        if let Some(mut child) = child_guard.take() {
            println!("[Test] Tearing down backend process...");
            let _ = child.kill();
            let _ = child.wait();
        }
    }

    fn reqwest_like_fetch(port: u16) -> Result<String, String> {
        // curl 커맨드를 활용해 모의 http fetch를 수행
        let url = format!("http://127.0.0.1:{}/api/health", port);
        let output = Command::new("curl")
            .arg("-s")
            .arg(url)
            .output()
            .map_err(|e| e.to_string())?;
        
        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).to_string())
        } else {
            Err(String::from_utf8_lossy(&output.stderr).to_string())
        }
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn test_resolve_release_sidecar_path_prefers_resources_binaries() {
        let base = std::env::temp_dir().join(format!("focal_node_test_{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        let macos_dir = base.join("Focal Node.app/Contents/MacOS");
        let res_dir = base.join("Focal Node.app/Contents/Resources");
        let res_bin = res_dir.join("binaries/focal_node_backend");
        std::fs::create_dir_all(&macos_dir).unwrap();
        std::fs::create_dir_all(res_bin.parent().unwrap()).unwrap();
        std::fs::write(&res_bin, b"sidecar").unwrap();

        let exe_path = macos_dir.join("focal_node");
        let resolved = resolve_release_sidecar_path(Some(&res_dir), &exe_path).unwrap();
        assert_eq!(resolved, res_bin);

        // Fallback when resource_dir is None still resolves Contents/Resources/binaries/
        let fallback = resolve_release_sidecar_path(None, &exe_path).unwrap();
        assert_eq!(fallback, res_bin);

        let _ = std::fs::remove_dir_all(&base);
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn test_resolve_release_sidecar_path_errors_when_missing() {
        let base = std::env::temp_dir().join(format!("focal_node_missing_{}", std::process::id()));
        let exe_path = base.join("Focal Node.app/Contents/MacOS/focal_node");
        let res_dir = base.join("Focal Node.app/Contents/Resources");
        let err = resolve_release_sidecar_path(Some(&res_dir), &exe_path).unwrap_err();
        assert!(err.contains("Backend sidecar binary not found"));
    }

    #[test]
    fn test_save_binary_file_rejects_unsafe_paths() {
        let base = std::env::temp_dir().join(format!("focal_node_save_sec_{}", std::process::id()));
        let sub = base.join("sub");
        let _ = std::fs::remove_dir_all(&base);
        std::fs::create_dir_all(&sub).unwrap();

        #[cfg(unix)]
        let symlink_target = base.join("symlink_report.pdf");
        #[cfg(unix)]
        let symlink_etc_dir = base.join("etc_link");
        #[cfg(unix)]
        {
            let real_file = base.join("real.pdf");
            std::fs::write(&real_file, b"%PDF-orig").unwrap();
            std::os::unix::fs::symlink(&real_file, &symlink_target).unwrap();
            std::os::unix::fs::symlink("/etc", &symlink_etc_dir).unwrap();
        }

        let mut cases: Vec<(&str, String)> = vec![
            ("empty", "".to_string()),
            ("whitespace", "   ".to_string()),
            ("nul_byte", format!("{}/bad\0.pdf", base.display())),
            ("relative", "relative_export.pdf".to_string()),
            ("trailing_slash", format!("{}/report.pdf/", base.display())),
            ("trailing_dot", format!("{}/report.pdf/.", base.display())),
            ("hidden_rc", base.join(".zshrc").to_string_lossy().to_string()),
            ("hidden_env", base.join(".env").to_string_lossy().to_string()),
            ("hidden_pdf", base.join(".secret.pdf").to_string_lossy().to_string()),
            ("traversal_pdf", format!("{}/../escape.pdf", sub.display())),
            ("shell_script", base.join("payload.sh").to_string_lossy().to_string()),
            ("exe_file", base.join("payload.exe").to_string_lossy().to_string()),
            ("plist_file", base.join("com.evil.agent.plist").to_string_lossy().to_string()),
            ("no_ext", base.join("README").to_string_lossy().to_string()),
            ("missing_parent", base.join("nonexistent_dir/report.pdf").to_string_lossy().to_string()),
            ("root_dir_file", "/report.pdf".to_string()),
            ("system_dir", "/System/evil.pdf".to_string()),
            ("library_dir", "/Library/evil.md".to_string()),
            ("usr_dir", "/usr/evil.pdf".to_string()),
            ("bin_dir", "/bin/evil.pdf".to_string()),
            ("sbin_dir", "/sbin/evil.pdf".to_string()),
            ("etc_dir", "/etc/evil.md".to_string()),
            ("private_etc_dir", "/private/etc/evil.md".to_string()),
            ("app_bundle_mixed_case", "/Applications/Focal Node.APP/contents/Resources/evil.md".to_string()),
        ];

        #[cfg(unix)]
        {
            cases.push(("symlink_target", symlink_target.to_string_lossy().to_string()));
            cases.push(("symlink_to_etc", symlink_etc_dir.join("evil.md").to_string_lossy().to_string()));
        }

        let outcomes: Vec<(&str, Result<(), String>)> = cases
            .into_iter()
            .map(|(label, candidate)| (label, save_binary_file(candidate, b"%PDF-1.4".to_vec())))
            .collect();

        let _ = std::fs::remove_dir_all(&base);

        for (label, outcome) in outcomes {
            assert!(outcome.is_err(), "Expected save_binary_file to reject {}, got {:?}", label, outcome);
        }
    }

    #[test]
    fn test_save_binary_file_allows_valid_pdf_and_markdown_exports() {
        let base = std::env::temp_dir().join(format!("focal_node_save_ok_{}", std::process::id()));
        let safe_dir = base.join("etc_backup");
        let _ = std::fs::remove_dir_all(&base);
        std::fs::create_dir_all(&safe_dir).unwrap();

        let pdf_path = safe_dir.join("photo_AI비평_리포트.pdf");
        let md_path = safe_dir.join("photo_AI비평.MD");

        let pdf_bytes = b"%PDF-1.7 test content".to_vec();
        let md_bytes = b"# Critique Report\n".to_vec();

        let pdf_outcome = save_binary_file(pdf_path.to_string_lossy().to_string(), pdf_bytes.clone());
        let md_outcome = save_binary_file(md_path.to_string_lossy().to_string(), md_bytes.clone());
        let overwrite_outcome = save_binary_file(md_path.to_string_lossy().to_string(), b"# Updated\n".to_vec());

        assert!(pdf_outcome.is_ok(), "Expected PDF export to succeed, got {:?}", pdf_outcome);
        assert!(md_outcome.is_ok(), "Expected MD export to succeed, got {:?}", md_outcome);
        assert!(overwrite_outcome.is_ok(), "Expected overwriting regular MD file to succeed, got {:?}", overwrite_outcome);
        assert_eq!(std::fs::read(&pdf_path).unwrap(), pdf_bytes);
        assert_eq!(std::fs::read(&md_path).unwrap(), b"# Updated\n");

        let _ = std::fs::remove_dir_all(&base);
    }

    #[test]
    fn test_tauri_conf_csp_hardening() {
        let conf_str = include_str!("../tauri.conf.json");
        let conf_json: serde_json::Value = serde_json::from_str(conf_str).expect("Valid tauri.conf.json");
        let security = &conf_json["app"]["security"];
        let csp = security["csp"].as_str().expect("app.security.csp must be a non-null string");

        assert!(csp.contains("default-src 'self'"));
        assert!(csp.contains("script-src 'self'"));
        assert!(!csp.contains("script-src 'self' 'unsafe-inline'"));
        assert!(!csp.contains("'unsafe-eval'"));
        assert!(csp.contains("style-src 'self' 'unsafe-inline'"));
        assert!(csp.contains("http://127.0.0.1:*"));
        assert!(csp.contains("http://localhost:*"));
        assert!(csp.contains("ws://localhost:*"));
        assert!(csp.contains("blob:"));
        assert!(csp.contains("data:"));
        assert!(csp.contains("ipc:"));
        assert!(csp.contains("object-src 'none'"));
        assert!(csp.contains("base-uri 'self'"));

        let disabled_mods = security["dangerousDisableAssetCspModification"]
            .as_array()
            .expect("dangerousDisableAssetCspModification must be configured for style-src");
        assert!(disabled_mods.iter().any(|entry| entry.as_str() == Some("style-src")));
    }
}
