#!/usr/bin/env python3
"""
Goowoo 狗窝 - 本地SQLite知识库 v2.1
v2.0: 重复合并、热点优先、定时备份
v2.1: 安全加固 - 内容大小限制、关键词长度限制、数据库大小警告
"""

import sqlite3
import sys
import os
import re
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
import difflib

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "gouwo.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "backups")

# 内容大小限制：单条最大 1MB（防止恶意填充）
MAX_CONTENT_SIZE = 1024 * 1024  # 1MB
MAX_KEYWORDS_SIZE = 10 * 1024   # 关键词最大 10KB

# 中文停用词
STOP_WORDS = {
    '的', '是', '在', '我', '有', '和', '就', '不', '也', '都', '要', '这', '那',
    '一个', '可以', '我们', '你', '他', '她', '它', '了', '着', '给', '对', '到',
    '能', '会', '去', '说', '看', '让', '好', '很', '等', '把', '被', '比', '但',
    '如果', '因为', '所以', '而且', '但是', '就是', '还是', '只是', '这个', '那个',
    '一些', '已经', '正在', '没有', '什么', '这样', '那样', '如何', '为什么',
}

def init_db():
    """初始化数据库表"""
    Path(os.path.dirname(DB_PATH)).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # v2.0: 新增 search_count (检索次数) 和 content_hash (内容哈希)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            content_hash TEXT,
            keywords TEXT,
            category TEXT,
            search_count INTEGER DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    ''')
    
    # FTS全文检索虚拟表
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts 
        USING fts5(id, content, keywords, content=knowledge, content_rowid=id)
    ''')
    
    # 触发器
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
            INSERT INTO knowledge_fts(rowid, id, content, keywords) 
            VALUES (new.id, new.id, new.content, new.keywords);
        END;
    ''')
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, id, content, keywords) 
            VALUES('delete', old.id, old.id, old.content, old.keywords);
        END;
    ''')
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, id, content, keywords) 
            VALUES('delete', old.id, old.id, old.content, old.keywords);
            INSERT INTO knowledge_fts(rowid, id, content, keywords) 
            VALUES (new.id, new.id, new.content, new.keywords);
        END;
    ''')
    
    conn.commit()
    conn.close()

def get_content_hash(content):
    """计算内容MD5哈希，用于重复检测"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def calculate_similarity(text1, text2):
    """计算两个文本的相似度（0-1）"""
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def find_similar(content, threshold=0.85):
    """查找相似内容，返回最相似的条目"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, content, keywords, category FROM knowledge')
    all_items = cursor.fetchall()
    conn.close()
    
    cleaned = clean_content(content)
    
    best_match = None
    best_ratio = 0
    
    for item in all_items:
        item_id, item_content, keywords, category = item
        ratio = calculate_similarity(cleaned, clean_content(item_content))
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = item
    
    return best_match, best_ratio

def extract_keywords(content, num_keywords=10):
    """提取关键词"""
    words = re.findall(r'[\w\u4e00-\u9fa5]+', content)
    words = [w for w in words if len(w) >= 2 and w not in STOP_WORDS]
    
    word_count = {}
    for word in words:
        word_count[word] = word_count.get(word, 0) + 1
    
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    keywords = [w[0] for w in sorted_words[:num_keywords]]
    
    result = ','.join(keywords)
    # 安全检查：关键词过长则截断
    if len(result) > MAX_KEYWORDS_SIZE:
        result = result[:MAX_KEYWORDS_SIZE]
        # 去掉最后一个不完整的词
        result = ','.join(result.rsplit(',', 1)[:-1])
    
    return result

def clean_content(content):
    """清洗内容"""
    content = re.sub(r'\n+', ' ', content)
    content = re.sub(r'\s+', ' ', content)
    return content.strip()

def add_content(content, keywords=None, category=None, auto_merge=True, merge_threshold=0.85):
    """添加内容，支持重复合并"""
    # 安全检查：内容大小限制
    if len(content) > MAX_CONTENT_SIZE:
        print(f"❌ 内容过大！最大 {MAX_CONTENT_SIZE // (1024*1024)}MB，当前 {len(content) // (1024*1024)}MB")
        return None
    
    content = clean_content(content)
    content_hash = get_content_hash(content)
    
    if not keywords:
        keywords = extract_keywords(content)
    
    init_db()
    now = datetime.now().isoformat()
    
    # 检查重复
    if auto_merge:
        similar, ratio = find_similar(content, merge_threshold)
        if similar:
            item_id, old_content, old_keywords, old_category = similar
            print(f"⚠️ 发现相似内容 (相似度 {ratio*100:.1f}%)")
            print(f"   已有ID: {item_id}")
            print(f"   新内容: {content[:80]}...")
            print(f"   已存内容: {old_content[:80]}...")
            print(f"\n是否合并？输入 y 合并到已有条目，n 新增，q 取消: ", end='')
            choice = input().strip().lower()
            
            if choice == 'y':
                # 合并关键词
                old_kw_set = set(old_keywords.split(',')) if old_keywords else set()
                new_kw_set = set(keywords.split(','))
                merged_kws = ','.join(old_kw_set | new_kw_set)
                update_content(item_id, content, merged_kws, category)
                return item_id
            elif choice == 'q':
                print("❌ 已取消")
                return None
            # 否则继续新增
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        '''INSERT INTO knowledge (content, content_hash, keywords, category, search_count, created_at, updated_at) 
           VALUES (?, ?, ?, ?, 0, ?, ?)''',
        (content, content_hash, keywords, category, now, now)
    )
    
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    
    print(f"✅ 内容已存入狗窝，ID: {last_id}")
    if category:
        print(f"📁 分类: {category}")
    print(f"🔑 关键词: {keywords}")
    print(f"📊 清洗后大小: {len(content)} 字符")
    return last_id

def update_content(item_id, new_content, keywords=None, category=None):
    """更新已有内容"""
    new_content = clean_content(new_content)
    if not keywords:
        keywords = extract_keywords(new_content)
    
    init_db()
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if category is not None:
        cursor.execute(
            '''UPDATE knowledge 
               SET content=?, content_hash=?, keywords=?, category=?, updated_at=? 
               WHERE id=?''',
            (new_content, get_content_hash(new_content), keywords, category, now, item_id)
        )
    else:
        cursor.execute(
            '''UPDATE knowledge 
               SET content=?, content_hash=?, keywords=?, updated_at=? 
               WHERE id=?''',
            (new_content, get_content_hash(new_content), keywords, now, item_id)
        )
    
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    
    if changed:
        print(f"✏️ 已更新 ID {item_id}")
    else:
        print(f"❌ 未找到 ID {item_id}")
    return changed

def search_content(keyword, boost_hot=True):
    """搜索，热点内容优先"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = keyword.replace(',', ' ').replace('，', ' ')
    
    # FTS搜索
    cursor.execute('''
        SELECT k.id, k.content, k.keywords, k.category, k.created_at, k.search_count
        FROM knowledge k
        JOIN knowledge_fts fts ON k.id = fts.rowid
        WHERE knowledge_fts MATCH ?
    ''', (query,))
    
    results = cursor.fetchall()
    
    if not results:
        # 降级模糊搜索
        cursor.execute('''
            SELECT id, content, keywords, category, created_at, search_count
            FROM knowledge 
            WHERE keywords LIKE ? OR content LIKE ?
        ''', (f'%{keyword}%', f'%{keyword}%'))
        results = cursor.fetchall()
    
    # 更新搜索次数
    for row in results:
        item_id = row[0]
        cursor.execute('UPDATE knowledge SET search_count = search_count + 1 WHERE id = ?', (item_id,))
    
    conn.commit()
    
    # 热点优先排序：search_count越高越靠前
    if boost_hot:
        results = sorted(results, key=lambda x: x[5] if x[5] else 0, reverse=True)
    
    conn.close()
    
    if not results:
        print("🔍 未找到相关内容")
        return []
    
    print(f"🔍 找到 {len(results)} 条相关内容 (热点优先):\n")
    for i, row in enumerate(results, 1):
        rid, content, keywords, category, created_at, search_count = row
        hot_indicator = "🔥" * min(search_count // 3, 5) if search_count else ""
        print(f"[{i}] ID: {rid} {hot_indicator}")
        if category:
            print(f"📁 分类: {category}")
        print(f"📅 创建: {created_at[:10]} | 🔥检索: {search_count}次")
        print(f"🔑 关键词: {keywords}")
        if len(content) <= 200:
            print(f"📝 内容: {content}")
        else:
            print(f"📝 内容: {content[:200]}...")
        print("-" * 60)
    
    return results

def backup():
    """覆盖式备份：只保留一份，每次覆盖"""
    init_db()
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    
    backup_file = os.path.join(BACKUP_DIR, "gouwo_backup.db")
    
    # 复制数据库（覆盖）
    shutil.copy2(DB_PATH, backup_file)
    
    print(f"✅ 备份完成（已覆盖）: {backup_file}")
    print(f"📁 备份目录: {BACKUP_DIR}")
    return backup_file

def restore(backup_file=None):
    """恢复备份（从单文件备份恢复）"""
    if not backup_file:
        backup_file = os.path.join(BACKUP_DIR, "gouwo_backup.db")
    
    if not os.path.exists(backup_file):
        print(f"❌ 备份文件不存在: {backup_file}")
        return False
    
    shutil.copy2(backup_file, DB_PATH)
    print(f"✅ 恢复完成: {DB_PATH}")
    return True

def get_full(item_id):
    """获取条目完整内容"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, content, keywords, category, created_at, search_count 
        FROM knowledge WHERE id = ?
    ''', (item_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print(f"❌ 未找到 ID {item_id}")
        return None
    
    rid, content, keywords, category, created_at, search_count = row
    hot = "🔥" * min(search_count // 3, 5) if search_count else ""
    
    print(f"\n📖 ID {rid} {hot} - 完整内容:\n")
    print(content)
    print(f"\n----------------------------------------")
    print(f"🔑 关键词: {keywords}")
    if category:
        print(f"📁 分类: {category}")
    print(f"📅 创建时间: {created_at}")
    print(f"🔥 检索次数: {search_count}")
    
    return row

def list_all(category=None, sort_by='hot'):
    """列出所有内容，支持按热点排序"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if category:
        cursor.execute('''
            SELECT id, content, keywords, category, created_at, search_count 
            FROM knowledge WHERE category = ?
            ORDER BY created_at DESC
        ''', (category,))
    else:
        cursor.execute('''
            SELECT id, content, keywords, category, created_at, search_count 
            FROM knowledge
            ORDER BY created_at DESC
        ''')
    
    results = cursor.fetchall()
    
    # 按热点排序
    if sort_by == 'hot':
        results = sorted(results, key=lambda x: x[5] if x[5] else 0, reverse=True)
    
    conn.close()
    
    if not results:
        if category:
            print(f"📚 分类 [{category}] 没有内容")
        else:
            print("📚 狗窝还是空的")
        return []
    
    if category:
        print(f"📚 分类 [{category}] 共 {len(results)} 条内容 (按热点排序):\n")
    else:
        print(f"📚 狗窝共 {len(results)} 条内容 (按热点排序):\n")
    
    for row in results:
        rid, content, keywords, cat, created_at, search_count = row
        cat_str = f" | {cat}" if cat else ""
        hot = "🔥" * min(search_count // 3, 5) if search_count else ""
        print(f"ID: {rid}{hot} | {created_at[:10]}{cat_str}")
        print(f"  {content[:60]}...")
    
    return results

def delete_item(item_id):
    """删除条目"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM knowledge WHERE id = ?', (item_id,))
    conn.commit()
    
    if cursor.rowcount > 0:
        print(f"🗑️ 已删除 ID {item_id}")
    else:
        print(f"❌ 未找到 ID {item_id}")
    
    conn.close()

def stats():
    """统计信息"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM knowledge')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(length(content)) FROM knowledge')
    total_chars = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(search_count) FROM knowledge')
    total_searches = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT AVG(search_count) FROM knowledge')
    avg_searches = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT DISTINCT category FROM knowledge WHERE category IS NOT NULL')
    categories = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('SELECT id, content, search_count FROM knowledge ORDER BY search_count DESC LIMIT 5')
    hot_items = cursor.fetchall()
    
    # 获取数据库文件大小
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    conn.close()
    
    print(f"📊 Goowoo 狗窝统计:")
    print(f"  总条目数: {total}")
    print(f"  总字符数: {total_chars}")
    print(f"  总检索次数: {total_searches}")
    print(f"  平均检索次数: {avg_searches:.1f}")
    print(f"  数据库大小: {db_size / (1024*1024):.2f} MB")
    print(f"  分类列表: {', '.join(categories) if categories else '无'}")
    print(f"  数据库文件: {DB_PATH}")
    print(f"  安全限制: 单条最大 {MAX_CONTENT_SIZE // (1024*1024)}MB")
    
    # 警告：数据库过大
    if db_size > 100 * 1024 * 1024:  # 超过 100MB
        print(f"\n⚠️ 警告：数据库已超过 100MB，建议清理或备份后新建库")
    
    if hot_items:
        print(f"\n🔥 热门内容 TOP5:")
        for item_id, content, count in hot_items:
            print(f"  ID {item_id}: {content[:40]}... (检索{count}次)")
    
    # 备份信息
    backup_file = os.path.join(BACKUP_DIR, "gouwo_backup.db")
    if os.path.exists(backup_file):
        mtime = datetime.fromtimestamp(os.path.getmtime(backup_file))
        print(f"\n💾 备份: {backup_file}")
        print(f"   更新时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return total, total_chars, categories

def show_help():
    """显示帮助"""
    help_text = """
🐶 狗窝 v2.0 - 本地SQLite知识库（升级版）

命令:
  add <内容> [关键词] [分类]    - 添加内容（自动检测重复）
  search <关键词>              - 搜索（热点优先）
  get <id>                    - 查看完整内容
  update <id> <内容> [关键词] - 更新内容
  list [分类]                  - 列出内容（默认热点排序）
  delete <id>                 - 删除条目
  stats                       - 统计信息
  backup                      - 备份数据库
  restore [文件]              - 恢复备份
  help                        - 显示帮助

新增功能:
  ✨ 重复合并: 添加时自动检测相似内容，可选择合并
  🔥 热点检索: 检索次数越多越靠前
  💾 定时备份: 覆盖式备份，保留最近3份

示例:
  python gouwo.py add "麟德智造3匹机组价格3300元" "麟德智造,价格" "产品"
  python gouwo.py search "机组"
  python gouwo.py list 产品
  python gouwo.py backup
"""
    print(help_text)

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        if len(sys.argv) < 3:
            print("❌ 请提供要存储的内容")
            return
        content = sys.argv[2]
        keywords = sys.argv[3] if len(sys.argv) > 3 else None
        category = sys.argv[4] if len(sys.argv) > 4 else None
        add_content(content, keywords, category)
    
    elif command == 'search':
        if len(sys.argv) < 3:
            print("❌ 请提供搜索关键词")
            return
        keyword = sys.argv[2]
        search_content(keyword)
    
    elif command == 'get':
        if len(sys.argv) < 3:
            print("❌ 请提供ID")
            return
        item_id = int(sys.argv[2])
        get_full(item_id)
    
    elif command == 'update':
        if len(sys.argv) < 4:
            print("❌ 请提供ID和新内容")
            return
        item_id = int(sys.argv[2])
        new_content = sys.argv[3]
        keywords = sys.argv[4] if len(sys.argv) > 4 else None
        category = sys.argv[5] if len(sys.argv) > 5 else None
        update_content(item_id, new_content, keywords, category)
    
    elif command == 'list':
        category = sys.argv[2] if len(sys.argv) > 2 else None
        list_all(category)
    
    elif command == 'delete':
        if len(sys.argv) < 3:
            print("❌ 请提供要删除的ID")
            return
        item_id = int(sys.argv[2])
        delete_item(item_id)
    
    elif command == 'stats':
        stats()
    
    elif command == 'backup':
        backup()
    
    elif command == 'restore':
        backup_file = sys.argv[2] if len(sys.argv) > 2 else None
        restore(backup_file)
    
    elif command == 'help':
        show_help()
    
    else:
        print(f"❌ 未知命令: {command}")
        show_help()

if __name__ == '__main__':
    main()
