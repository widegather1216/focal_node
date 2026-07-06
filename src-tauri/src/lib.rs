use std::io::{BufRead, BufReader};
use std::process::{Command, Stdio, Child};
use std::sync::{Arc, Mutex, Condvar};
use std::thread;
use regex::Regex;
use tauri::{Manager, Emitter};

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
        .invoke_handler(tauri::generate_handler![get_api_port, reveal_in_finder])
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state_for_thread = state_clone.clone();

            thread::spawn(move || {
                let current_dir = std::env::current_dir().unwrap_or_default();
                
                // 개발 환경인 경우 backend/app/main.py 기동
                // 릴리즈 환경인 경우 sidecar 바이너리 기동
                let (program, args) = if cfg!(debug_assertions) {
                    let mut script_path = current_dir.join("backend/app/main.py");
                    for prefix in &["", "../", "../../"] {
                        let path = current_dir.join(prefix).join("backend/app/main.py");
                        if path.exists() {
                            script_path = path;
                            break;
                        }
                    }
                    
                    ("python3".to_string(), vec![script_path.to_string_lossy().to_string()])
                } else {
                    let exe_path = std::env::current_exe().unwrap();
                    let sidecar_name = if cfg!(target_os = "windows") {
                        "focal_node_backend.exe"
                    } else {
                        "focal_node_backend"
                    };
                    let sidecar_path = exe_path.parent().unwrap().join(sidecar_name);
                    
                    (sidecar_path.to_string_lossy().to_string(), vec![])
                };

                println!("[Tauri Rust] Spawning backend: {} {:?}", program, args);

                let mut cmd = Command::new(&program);
                cmd.args(&args);
                cmd.stdout(Stdio::piped());
                cmd.stderr(Stdio::piped());

                let mut child = match cmd.spawn() {
                    Ok(c) => c,
                    Err(e) => {
                        let err_msg = format!("Failed to spawn backend process: {}", e);
                        eprintln!("[Tauri Rust] {}", err_msg);
                        {
                            let mut err_guard = state_for_thread.error.lock().unwrap();
                            *err_guard = Some(err_msg);
                        }
                        let _port_guard = state_for_thread.port.lock().unwrap();
                        state_for_thread.condvar.notify_all();
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

                    let reader = BufReader::new(stdout);
                    let re_port = Regex::new(r"\[Sidecar\] PORT:\s*(\d+)").unwrap();
                    let re_indexing = Regex::new(r"\[Indexing\] Progress:\s*(\d+)/(\d+)\s*-\s*(.*)").unwrap();
                    let re_indexing_start = Regex::new(r"\[Indexer\] Starting background indexing\. Found\s*(\d+)\s*files\.").unwrap();
                    
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
                            } else if line_str.contains("[Downloader] Completed") || line_str.contains("Model loaded successfully.") || line_str.contains("Model unloaded.") {
                                let _ = app_handle.emit("model-download-completed", ());
                            } else if line_str.contains("[Indexer] Background indexing completed.") {
                                let _ = app_handle.emit("indexing-completed", ());
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
}
