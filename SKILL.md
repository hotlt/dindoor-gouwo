---
name: dindoor-gouwo
description: Goowoo 狗窝 - 轻量级本地 SQLite 知识库 v2.0，支持内容存入、全文检索、分类管理、自动清洗、重复合并、热点优先检索、定时备份。
metadata: {"clawdbot":{"emoji":"🐶","requires": ["python3", "sqlite3"]}}
---

# 🐶 Goowoo 狗窝 v2.0 - 本地知识库

轻量级本地 SQLite 知识库，为 OpenClaw AI 助手打造的持久记忆系统。

## 特性

- ✅ **自动数据清洗** - 去除多余空行空格，压缩体积，保持整洁
- ✅ **FTS 全文检索** - SQLite 内置全文搜索，快速准确
- ✅ **分类标签** - 支持给内容添加分类，方便筛选管理
- ✅ **内容更新** - 支持更新已有条目
- ✅ **查看全文** - 搜索结果支持直接查看完整内容
- ✅ **零依赖** - 只需要 Python 标准库

### v2.0 新增功能

- 🔥 **热点优先检索** - 检索次数越多，排序越靠前，热点内容更快找到
- 🔄 **重复内容合并** - 相似度检测，自动提示合并，避免数据冗余
- 💾 **定时备份** - 覆盖式备份，保留最近3份，防止文件损坏

## 安装方式

### 方式一：SkillHub 一键安装（推荐）
```bash
skillhub install dindoor-gouwo
```

### 方式二：Git 手动安装
```bash
# GitHub
git clone https://github.com/hotlt/goowoo.git dindoor-gouwo

# Gitee（国内加速）
git clone https://gitee.com/dindoor/goowoo.git dindoor-gouwo
```

## 命令说明

| 命令 | 用法 | 说明 |
|------|------|------|
| `add` | `add "内容" [关键词] [分类]` | 添加内容，自动提取关键词，检测重复 |
| `search` | `search "关键词"` | FTS 全文搜索，热点优先排序 |
| `get` | `get <id>` | 获取条目的完整内容 |
| `update` | `update <id> "新内容" [关键词]` | 更新已有内容 |
| `list` | `list [分类]` | 列出所有内容，按热点排序 |
| `delete` | `delete <id>` | 删除指定ID条目 |
| `stats` | `stats` | 显示数据库统计信息 |
| `backup` | `backup` | 备份数据库（覆盖式） |
| `restore` | `restore [文件]` | 从备份恢复 |
| `help` | `help` | 显示帮助 |

## 使用示例

```bash
# 添加内容，自动提取关键词
python3 scripts/gouwo.py add "麟德智造3匹机组仅售3300元" "麟德智造,价格,机组" "产品"

# 搜索内容（热点优先）
python3 scripts/gouwo.py search "价格"

# 查看完整内容
python3 scripts/gouwo.py get 1

# 列出"产品"分类下的所有内容
python3 scripts/gouwo.py list 产品

# 备份数据库
python3 scripts/gouwo.py backup

# 查看统计
python3 scripts/gouwo.py stats
```

## 数据结构

- 数据库位置：`data/gouwo.db`
- 备份目录：`data/backups/`（保留最近3份）
- 数据表：`knowledge` + FTS 虚拟表 `knowledge_fts`

### 字段说明

| 字段 | 说明 |
|------|------|
| id | 唯一标识 |
| content | 原始内容 |
| content_hash | 内容MD5哈希（用于重复检测） |
| keywords | 提取的关键词 |
| category | 分类标签 |
| search_count | 检索次数（热点排序用） |
| created_at | 创建时间 |
| updated_at | 更新时间 |

## AI 代理使用说明

当用户说：
- **"把这些内容存到狗窝"** - 调用 `add` 命令存储
- **"从狗窝查询xxx"** - 调用 `search` 命令搜索
- **"从狗窝列出所有"** - 调用 `list` 命令

关键词用户不指定则自动提取，分类用户不说则留空。

## 作者

🐕 Goowoo 天涯 AI (tianya-claw) @ OpenClaw | v2.0 升级于 2026-03-24
MIT License - 允许自由使用、分发
