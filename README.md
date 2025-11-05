# intrising_workspace_monitor

A lightweight workspace sentinel that **monitors GitHub issues**, **auto-reviews pull requests**, and **sends email digests/alerts**. It can also **assemble and publish FQC Reports** from CI artifacts to keep engineering and QA in sync.

---

## ✨ Features

- **Issue Watcher**
  - Track new/updated/closed issues across repositories
  - SLA & stale detection with auto-labels/assignees
  - Daily/weekly digests (configurable time & recipients)

- **PR Reviewer**
  - Enforce PR template completeness (title, linked issue, evidence)
  - Policy checks: required labels, forbidden/allowed paths
  - Gate on CI signals (failed checks, lint errors, coverage drop)
  - Auto-comments with actionable guidance (e.g., Conventional Commits)

- **Email Notifications**
  - Realtime alerts for critical labels (`bug`, `security`, `customer`)
  - Scheduled summaries (e.g., 08:30 Asia/Taipei)
  - Rich context: links to PR/issue, CI runs, artifacts

- **FQC Report Publisher**
  - Pull results from CI (e.g., Jenkins) and assemble a standardized **FQC Report** (PDF/DOCX)
  - Version-aligned naming (e.g., `V1.02.0078_17_FQC_Report.pdf`)
  - One-click distribution via email and archival link

---

## 🧱 Architecture (at a glance)

- **Webhook/Worker**: consumes GitHub events & scheduled jobs  
- **Rules Engine**: evaluates policy (issues/PRs/CI/coverage)  
- **Mailer**: alerts + daily/weekly digests  
- **FQC Publisher**: fetches CI artifacts → composes report → sends

---

## 🚀 Quick Start

### 1) Prerequisites
- GitHub App or PAT with minimal scopes (see **Security**)
- SMTP credentials (or API key) for outbound email
- Optional: Jenkins/CI endpoint for FQC artifacts

### 2) Configuration
Create `config.yaml` at repo root:

```yaml
github:
  app_id: YOUR_APP_ID
  private_key_path: ./secrets/github-app.pem
  repos:
    - intrising/os6
    - intrising/os2pro
  reviewers:
    required_approvals: 2
    block_on:
      - "ci:failed"
      - "lint:error"
      - "coverage:drop>2%"   # block merge if coverage drops >2%
  rules:
    require_template: true
    require_issue_link: true
    critical_labels: ["bug","security","customer"]
    forbid_paths:
      - "/etc/version.cfg"
    allow_paths:
      - "docs/**"
      - "changelog/**"

notifications:
  email:
    smtp_host: smtp.example.com
    smtp_user: noreply@example.com
    smtp_pass: ${SMTP_PASS}
    daily_digest_time: "08:30"   # Asia/Taipei by default
    to: ["pm@intrising.com.tw","qa@intrising.com.tw"]
    cc: ["khkh@intrising.com.tw"]

fqc:
  enable: true
  ci_artifacts_url: "https://jenkins.example/job/FQC/${VERSION}/artifact/"
  version_pattern: "V\\d+\\.\\d+\\.\\d+(_[a-z]\\d+)?"
  output_name: "${VERSION}_FQC_Report.pdf"
  recipients:
    to: ["customer@partner.com"]
    cc: ["qa@intrising.com.tw","pm@intrising.com.tw"]
```
