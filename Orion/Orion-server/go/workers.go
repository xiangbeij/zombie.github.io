package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"
)

const scanTimeout = 10 * time.Minute

type job struct {
	taskID   string
	url      string
	scanType string
}

var jobQueue = make(chan job, 2000)
var wg sync.WaitGroup

func startWorkerPool(n int) {
	for i := 0; i < n; i++ {
		go func() {
			for j := range jobQueue {
				execScan(j.taskID, j.url, j.scanType)
			}
		}()
	}
	log.Printf("[workers] pool started with %d goroutines", n)
}

func submitScan(taskID, url, scanType string) {
	select {
	case jobQueue <- job{taskID: taskID, url: url, scanType: scanType}:
		TasksMu.Lock()
		if t, ok := Tasks[taskID]; ok {
			t.Status = "pending"
		}
		TasksMu.Unlock()
	default:
		TasksMu.Lock()
		if t, ok := Tasks[taskID]; ok {
			t.Status = "error"
			t.Error = "Scan queue is full, please try again later"
			t.FinishedAt = time.Now()
			Stats.Error++
		}
		TasksMu.Unlock()
		Stats.Total--
	}
}

func execScan(taskID, targetURL, scanType string) {
	wg.Add(1)
	defer wg.Done()

	TasksMu.Lock()
	if t, ok := Tasks[taskID]; ok {
		t.Status = "running"
		t.StartedAt = time.Now()
	}
	Stats.Running++
	TasksMu.Unlock()

	result, err := runLibraScan(targetURL, scanType)

	TasksMu.Lock()
	defer TasksMu.Unlock()

	if t, ok := Tasks[taskID]; ok {
		t.FinishedAt = time.Now()
		t.Progress = 100
		if err != nil {
			t.Status = "error"
			t.Error = err.Error()
			Stats.Error++
		} else {
			t.Status = "success"
			t.Result = result
			Stats.Success++
		}
	}
	if Stats.Running > 0 {
		Stats.Running--
	}
	go saveState()
}

func runLibraScan(targetURL, scanType string) (*ScanResult, error) {
	libraPy := filepath.Join(*baseDir, "orion.py")
	done := make(chan struct{})
	var stdout []byte
	var errRun error

	go func() {
		cmd := exec.Command("python3", libraPy, "-u", targetURL, "-t", scanType)
		cmd.Dir = *baseDir
		cmd.Env = append(os.Environ(),
			fmt.Sprintf("PYTHONPATH=%s", *baseDir),
			"PYTHONIOENCODING=utf-8",
		)
		stdout, errRun = cmd.CombinedOutput()
		close(done)
	}()

	select {
	case <-done:
	case <-time.After(scanTimeout):
		return nil, fmt.Errorf("Scan timeout after %v. Target may be slow or unresponsive.", scanTimeout)
	}

	if errRun != nil {
		snippet := strings.TrimSpace(string(stdout))
		if len(snippet) > 300 {
			snippet = snippet[:300]
		}
		errMsg := snippet
		if strings.Contains(snippet, "Name or service not known") || strings.Contains(snippet, "getaddrinfo") || strings.Contains(snippet, "Could not resolve") {
			errMsg = "DNS resolution failed. Please check if the URL is correct and the domain is accessible."
		} else if strings.Contains(snippet, "Connection refused") || strings.Contains(snippet, "ECONNREFUSED") {
			errMsg = "Connection refused. Target port 80/443 is unreachable. Please confirm the service is running."
		} else if strings.Contains(snippet, "Connection timed out") || strings.Contains(snippet, "ETIMEDOUT") || strings.Contains(snippet, "timed out") {
			errMsg = "Connection timeout. Please check if the target is reachable or the server is responding too slowly."
		} else if strings.Contains(snippet, "SSL") || strings.Contains(snippet, "TLS") || strings.Contains(snippet, "certificate") {
			errMsg = "TLS/SSL certificate error. Please confirm the target uses a valid HTTPS certificate."
		} else if strings.Contains(snippet, "No route to host") || strings.Contains(snippet, "Network is unreachable") {
			errMsg = "Network unreachable. Please confirm the target is on the same network or firewall allows access."
		} else if strings.Contains(snippet, "400") || strings.Contains(snippet, "Bad Request") {
			errMsg = "HTTP 400 Bad Request. URL format may be incorrect."
		} else if strings.Contains(snippet, "403") || strings.Contains(snippet, "Forbidden") {
			errMsg = "HTTP 403 Forbidden. Target may have anti-crawl protection (WAF)."
		} else if strings.Contains(snippet, "404") || strings.Contains(snippet, "Not Found") {
			errMsg = "HTTP 404 Not Found. The URL may have expired or the path is incorrect."
		} else if snippet == "" {
			errMsg = "Scan process exited with no output. Please check if the target is accessible and Python environment is working."
		}
		return nil, fmt.Errorf("%s", errMsg)
	}

	// Strip ANSI escape codes
	ansi := regexp.MustCompile("\x1b\\[[0-9;]*[a-zA-Z]")
	out := ansi.ReplaceAllString(string(stdout), "")

	return parseScanOutput(out)
}

func parseScanOutput(output string) (*ScanResult, error) {
	lines := strings.Split(output, "\n")
	depth := 0
	start := -1
	for i := len(lines) - 1; i >= 0; i-- {
		l := strings.TrimSpace(lines[i])
		for _, ch := range l {
			if ch == '{' {
				if depth == 0 {
					start = i
				}
				depth++
			} else if ch == '}' {
				depth--
			}
		}
		if depth == 0 && start >= 0 {
			break
		}
	}
	if start < 0 {
		return nil, fmt.Errorf("no valid JSON found in scan output")
	}
	var result ScanResult
	if err := json.Unmarshal([]byte(strings.Join(lines[start:], "")), &result); err != nil {
		return nil, fmt.Errorf("failed to parse scan result: %v", err)
	}
	return &result, nil
}

func min(a, b int) int { if a < b { return a }; return b }
