import pymongo
from pymongo import UpdateOne
import networkx as nx
import json
from tqdm import tqdm  # 添加进度条

# 连接到 MongoDB
client = pymongo.MongoClient("localhost", 27017)
db = client["nankai_news"]
collection = db["news"]

# 创建有向图
G = nx.DiGraph()

# 使用批处理从 MongoDB 读取数据并构建图
batch_size = 1000
total_docs = collection.count_documents({})

print("开始构建图...")
for document in tqdm(collection.find().batch_size(batch_size), total=total_docs):
    url = document["url"]
    page_links = document.get("page_link", [])

    # 确保图中包含当前页面的节点
    if not G.has_node(url):
        G.add_node(url)

    # 检查并移除包含"download"的链接
    links_to_remove = [link for link in page_links if "download" in link]
    if links_to_remove:
        collection.update_one(
            {"_id": document["_id"]},
            {"$pull": {"page_link": {"$in": links_to_remove}}}
        )
        page_links = [link for link in page_links if link not in links_to_remove]

    # 添加边
    for link in page_links:
        if url != link:
            if not G.has_node(link):
                G.add_node(link)
            G.add_edge(url, link)

print("计算 PageRank...")
try:
    # 使用自定义参数计算PageRank
    pagerank_scores = nx.pagerank(G, alpha=0.85, max_iter=100, tol=1e-6)
except nx.PowerIterationFailedConvergence:
    print("PageRank算法未收敛，尝试调整参数...")
    # 如果未收敛，使用更宽松的参数重试
    pagerank_scores = nx.pagerank(G, alpha=0.85, max_iter=200, tol=1e-5)

# 将结果排序
sorted_scores = sorted(pagerank_scores.items(), key=lambda x: x[1], reverse=True)
sorted_url_scores = {url: score for url, score in sorted_scores}

# 保存到JSON文件
print("保存PageRank分数到JSON文件...")
with open('./pagerank.json', 'w', encoding='utf-8') as file:
    json.dump(sorted_url_scores, file, ensure_ascii=False, indent=4)

# 批量更新MongoDB
print("更新MongoDB中的PageRank分数...")
bulk_operations = []
batch_counter = 0
total_urls = len(pagerank_scores)

for url, score in tqdm(pagerank_scores.items(), total=total_urls):
    bulk_operations.append(
        UpdateOne(
            {"url": url},
            {"$set": {"pagerank_score": score}}
        )
    )
    batch_counter += 1

    # 每1000条执行一次批量更新
    if batch_counter >= 1000:
        try:
            collection.bulk_write(bulk_operations)
            bulk_operations = []
            batch_counter = 0
        except Exception as e:
            print(f"批量更新出错: {str(e)}")
            bulk_operations = []
            batch_counter = 0

# 处理剩余的更新操作
if bulk_operations:
    try:
        collection.bulk_write(bulk_operations)
    except Exception as e:
        print(f"最后一批更新出错: {str(e)}")

print("PageRank分数更新完成！")

# 关闭MongoDB连接
client.close()