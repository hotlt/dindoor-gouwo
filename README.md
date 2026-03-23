# 🐶 dindoor-gouwo (狗窝知识库)

轻量级本地 SQLite 知识库 for OpenClaw AI 代理。

在 OpenClaw 中一键安装：
```bash
skillhub install dindoor-gouwo
```

## 特性

- ✅ **自动数据清洗** - 去除多余空行空格，压缩体积
- ✅ **自动关键词提取** - 基于词频统计，自动过滤中文停用词
- ✅ **FTS 全文检索** - SQLite 内置全文搜索，快速准确
- ✅ **分类标签** - 支持给内容添加分类，方便筛选管理
- ✅ **内容更新** - 支持更新已有条目
- ✅ **零依赖** - 只需要 Python 标准库，不需要额外安装包

## 命令说明

| 命令 | 用法 | 说明 |
|------|------|------|
| `add` | `add "内容" [关键词] [分类]` | 添加内容到狗窝，关键词自动提取 |
| `search` | `search "关键词"` | FTS 全文搜索相关内容 |
| `get` | `get <id>` | 获取条目的完整内容 |
| `update` | `update <id> "新内容" [关键词]` | 更新已有内容 |
| `list` | `list [分类]` | 列出所有内容，可按分类筛选 |
| `delete` | `delete <id>` | 删除指定ID条目 |
| `stats` | `stats` | 显示数据库统计信息 |
| `help` | `help` | 显示帮助 |

## 使用示例

```bash
# 添加内容，自动提取关键词
python3 skills/dindoor-gouwo/scripts/gouwo.py add "麟德智造3匹机组仅售3300元" "麟德智造,价格,机组" "产品"

# 搜索内容
python3 skills/dindoor-gouwo/scripts/gouwo.py search "价格"

# 查看完整内容
python3 skills/dindoor-gouwo/scripts/gouwo.py get 1

# 列出"产品"分类下的所有内容
python3 skills/dindoor-gouwo/scripts/gouwo.py list 产品
```

## 数据存储

- 数据库位置：`data/gouwo.db`（相对于工作目录）
- 数据表：`knowledge` + FTS 虚拟表 `knowledge_fts`
- 自动维护全文索引，增删改自动更新

## AI 代理使用

当用户说：
- **"把这些内容存到狗窝"** - 调用 `add` 命令存储内容，自动清洗提取关键词
- **"从狗窝查询xxx"** - 调用 `search` 命令搜索并返回结果
- **"从狗窝列出"** - 调用 `list` 命令列出内容

关键词未指定时自动提取，分类未指定时留空。

## 作者

[dindoor](https://github.com/hotlt)

## License

MIT
