package main

import (
	"database/sql"
	"os"
	"path/filepath"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

func openDB(path string) (*sql.DB, error) {
	if _, err := os.Stat(path); err != nil {
		return nil, err
	}
	if db == nil {
		var err error
		db, err = sql.Open("sqlite3", path)
		if err != nil {
			return nil, err
		}
		db.SetMaxOpenConns(4)
		db.SetMaxIdleConns(2)
	}
	return db, nil
}

// ─── PDF Generation ───────────────────────────────────────────────────────

func generatePDF(task *Task) (string, error) {
	html := renderHTML(task)
	tmpHTML := filepath.Join(os.TempDir(), "libra_"+task.ID+".html")
	if err := os.WriteFile(tmpHTML, []byte(html), 0644); err != nil {
		return "", err
	}
	defer os.Remove(tmpHTML)

	pdfPath := filepath.Join(os.TempDir(), "libra_"+task.ID+".pdf")

	// Try weasyprint, then wkhtmltopdf
	for _, bin := range []string{"weasyprint", "wkhtmltopdf"} {
		if err := runExternalCmd(bin, tmpHTML, pdfPath); err == nil {
			return pdfPath, nil
		}
	}
	// No PDF tools available - serve HTML instead
	return tmpHTML, nil
}

func renderHTML(t *Task) string {
	result := t.Result
	rows := ""
	if result != nil {
		addRows := func(typ string, items []Link) {
			for _, it := range items {
				for _, r := range it.Results {
					rows += htmlRow(typ, it.URL, r, strJoin(it.Master))
				}
			}
		}
		addRows("Blacklink", result.BlacklinkList)
		addRows("Backdoor", result.BackdoorList)
		addRows("Violative", result.ViolativelinkList)
		for _, d := range result.DiedlinkList {
			rows += htmlRow("DeadLink", d.URL, d.StatusCode, strJoin(d.Master))
		}
	}
	return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>ShieldEye Scan Report</title>
<style>
body{font-family:Inter,'PingFang SC',sans-serif;margin:40px;background:#f8f9fb;color:#1a1a2e}
h1{color:#1a1a2e}
.meta{color:#5a6474;font-size:13px;margin-bottom:24px}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden}
th{background:#f8f9fb;color:#3c4a5c;padding:12px 16px;text-align:left;font-size:13px}
td{padding:10px 16px;border-top:1px solid #e8eaed;font-size:13px}
tr:hover{background:#f0f4ff}
.badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600}
.bl{background:#ffeaea;color:#d93636}.bd{background:#fff4e5;color:#c87c00}.vl{background:#fff4e5;color:#c87c00}.dl{background:#f0f2f5;color:#5a6474}
</style></head><body>
<h1>ShieldEye 安全扫描报告</h1>
<div class="meta">
  <p><strong>任务ID:</strong> ` + t.ID + ` &nbsp; <strong>URL:</strong> ` + t.URL + ` &nbsp; <strong>类型:</strong> ` + t.ScanType + `</p>
  <p><strong>状态:</strong> ` + t.Status + ` &nbsp; <strong>时间:</strong> ` + t.CreatedAt.Format("2006-01-02 15:04:05") + `</p>
</div>
<table><thead><tr><th>类型</th><th>URL</th><th>详情</th><th>Master</th></tr></thead><tbody>` + rows + `</tbody></table></body></html>`
}

func htmlRow(typ, url, detail, master string) string {
	cls := map[string]string{
		"Blacklink": "bl", "Backdoor": "bd", "Violative": "vl", "DeadLink": "dl",
	}[typ]
	return "<tr><td><span class=\"badge " + cls + "\">" + typ + "</span></td><td>" + url + "</td><td>" + detail + "</td><td>" + master + "</td></tr>"
}

func strJoin(s []string) string {
	if len(s) == 0 {
		return "-"
	}
	return strings.Join(s, "; ")
}
