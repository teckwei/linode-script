# 🗺️ Linode Region Capability Exporter

## ✅ Objective

Create an automated Python utility to extract Linode region capabilities using the `linode-cli`, format the output with user-friendly column titles, and export the results to a clean, readable CSV file. This helps in quickly identifying which regions support specific services such as GPU Linodes, Managed Databases, Kubernetes, and more.

---

## ❗ Problem Statement

Linode’s `linode-cli regions list` command outputs raw JSON, which:

- Is not human-readable at a glance.
- Makes it hard to compare region capabilities visually.
- Has technical identifiers for services that may not be obvious to end users.
- Isn’t optimized for sharing or quick spreadsheet analysis.

---

## 📝 Summary

This project provides:

- A **Python script** that calls the Linode CLI, processes the JSON response, and outputs a clean CSV.
- **Custom column titles** that make capabilities more understandable.
- **"Yes"/"No" markers** in the table to show service availability by region.
- A result file: `linode_regions.csv` for reporting or analysis.

---

## ⚙️ Setup Guide

### 🔧 Prerequisites

1. **Python 3.7+** installed.
2. **Linode CLI** installed and authenticated:
   ```bash
   pip install linode-cli
   linode-cli configure
   ```
3. Required Python libraries:
   ```bash
   pip install pandas
   ```

---

## 📥 Installation

Clone this repo or copy the script into your working directory.

---

## ▶️ Usage

Run the script from your terminal:
```bash
python linode_region_export.py
```

This will generate `linode_regions.csv` in the same directory.

---

## 📁 Output Example

| ID     | Country     | Linodes (Shared, Dedicated, High Memory Plan) | GPU Linodes (RTX 6000/RTX 4000 Ada) | Kubernetes | Block Storage | Managed Databases (MYSQL & PostgreSQL) | ... |
|--------|-------------|-----------------------------------------------|-------------------------------------|------------|----------------|-----------------------------------------|-----|
| ap-south | Singapore | Yes                                           | No                                  | Yes        | Yes            | Yes                                     |     |

---

## 🧩 Custom Column Titles

The following Linode capabilities have been renamed for clarity:

| Original Capability           | Custom Title                                        |
|------------------------------|-----------------------------------------------------|
| Linodes                      | Linodes (Shared, Dedicated, High Memory Plan)       |
| GPU Linodes                  | GPU Linodes (RTX 6000/RTX 4000 Ada)                 |
| Managed Databases            | Managed Databases (MYSQL & PostgreSQL)             |
| LA Disk Encryption           | LA Disk Encryption                                  |
| Cloud Firewall               | Cloud Firewall                                      |
| ...                          | ...                                                 |
