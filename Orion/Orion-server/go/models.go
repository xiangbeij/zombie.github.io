package main

import (
	"sync"
	"time"

	"github.com/robfig/cron/v3"
)

// ─── Task ─────────────────────────────────────────────────────────────────────

type Task struct {
	ID         string      `json:"id"`
	URL        string      `json:"url"`
	ScanType   string      `json:"scan_type"`
	Status     string      `json:"status"` // pending | running | success | error | timeout
	Progress   int         `json:"progress"`
	Result     *ScanResult `json:"result,omitempty"`
	Error      string      `json:"error,omitempty"`
	CreatedAt  time.Time   `json:"created_at"`
	StartedAt  time.Time   `json:"started_at,omitempty"`
	FinishedAt time.Time   `json:"finished_at,omitempty"`
}

// ─── Scan Result ──────────────────────────────────────────────────────────────

type ScanResult struct {
	TaskURL            string   `json:"taskurl"`
	TaskType          string   `json:"tasktype"`
	Status            string   `json:"status"`
	BlacklinkList     []Link   `json:"blacklink_list"`
	BackdoorList      []Link   `json:"backdoor_list"`
	ViolativelinkList []Link   `json:"violativelink_list"`
	DiedlinkList      []Died   `json:"diedlink_list"`
	DateTime          string   `json:"datetime"`
}

type Link struct {
	URL     string   `json:"url"`
	Results []string `json:"blacklinkres"`
	Master  []string `json:"master"`
}

type Died struct {
	URL        string   `json:"url"`
	StatusCode string      `json:"status_code"`
	Master     []string `json:"master"`
}

// ─── Batch ───────────────────────────────────────────────────────────────────

type Batch struct {
	ID        string    `json:"id"`
	URLs      []string  `json:"urls"`
	ScanType  string    `json:"scan_type"`
	Status    string    `json:"status"` // running | done | paused
	Total     int       `json:"total"`
	Completed int       `json:"completed"`
	Success   int       `json:"success"`
	Error     int       `json:"error"`
	TaskIDs   []string  `json:"task_ids"`
	CreatedAt time.Time `json:"created_at"`
}

// ─── Schedule ────────────────────────────────────────────────────────────────

type ScheduleJob struct {
	ID           string    `json:"id"`
	Name         string    `json:"name"`
	URL          string    `json:"url"`
	ScanType     string    `json:"scan_type"`
	CronExpr     string    `json:"cron_expr"`
	Enabled      bool      `json:"enabled"`
	NextRun      string    `json:"next_run,omitempty"`
	LastRun      string    `json:"last_run,omitempty"`
	CreatedAt    time.Time `json:"created_at"`
	CronEntryID  cron.EntryID `json:"-"`
}

// ─── In-memory stores ────────────────────────────────────────────────────────

var (
	Tasks     = make(map[string]*Task)
	TasksMu   sync.RWMutex

	Batches   = make(map[string]*Batch)
	BatchesMu sync.RWMutex

	SchedJobs = make(map[string]*ScheduleJob)
	SchedMu   sync.RWMutex

	Stats   = struct{ Total, Success, Error, Running int }{}
	StatsMu sync.RWMutex
)
