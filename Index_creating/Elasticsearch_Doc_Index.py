import pymongo
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from datetime import datetime
import os
import io
import tempfile
from bson import ObjectId

# 文档处理库
import PyPDF2
from docx import Document
import xlrd
import win32com.client
import pythoncom


class DocumentIndexer:
    def __init__(self,
                 mongo_host='localhost',
                 mongo_port=27017,
                 mongo_db='nankai_docs',
                 es_host='localhost',
                 es_port=9200,
                 index_name='nankai_docs_index'):
        # MongoDB连接
        self.mongo_client = pymongo.MongoClient(mongo_host, mongo_port)
        self.mongo_db = self.mongo_client[mongo_db]
        self.files_collection = self.mongo_db['docs']
        self.chunks_collection = self.mongo_db['docs_chunks']

        # Elasticsearch连接
        self.es = Elasticsearch(
            [f'http://{es_host}:{es_port}'],
            basic_auth=('elastic', '123456'),
            timeout=600,
            max_retries=3,
            retry_on_timeout=True
        )
        self.index_name = index_name

        # 初始化COM组件（用于处理旧版Office文档）
        pythoncom.CoInitialize()

    def get_file_data(self, file_id):
        """从fs.chunks集合获取完整的文件数据"""
        try:
            # 查找所有相关的chunks并按n排序
            chunks = self.chunks_collection.find(
                {'files_id': ObjectId(file_id)}
            ).sort('n', pymongo.ASCENDING)

            # 合并所有chunks的数据
            file_data = b''
            for chunk in chunks:
                file_data += chunk['data']

            return file_data
        except Exception as e:
            print(f"获取文件数据错误: {str(e)}")
            return None

    def create_index(self):
        """创建Elasticsearch索引"""
        settings = {
            "index": {
                "number_of_replicas": 2,
                "number_of_shards": 1
            },
            "analysis": {
                "analyzer": {
                    "chinese_analyzer": {
                        "type": "custom",
                        "tokenizer": "ik_max_word",
                        "filter": ["lowercase", "stop"]
                    },
                    "ik_smart_pinyin": {
                        "type": "custom",
                        "tokenizer": "ik_smart",
                        "filter": ["lowercase", "pinyin_filter"]
                    }
                },
                "filter": {
                    "pinyin_filter": {
                        "type": "pinyin",
                        "keep_full_pinyin": True,
                        "keep_joined_full_pinyin": True,
                        "keep_original": True,
                        "limit_first_letter_length": 16,
                        "remove_duplicated_term": True
                    }
                }
            }
        }

        mappings = {
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "ik_max_word",  # 使用 ik_max_word 进行索引分词
                    "search_analyzer": "ik_smart",  # 使用 ik_smart 进行搜索分词
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        },
                        "pinyin": {
                            "type": "text",
                            "analyzer": "ik_smart_pinyin"
                        }
                    }
                },
                "content": {
                    "type": "text",
                    "analyzer": "ik_max_word",  # 使用 ik_max_word 进行索引分词
                    "search_analyzer": "ik_smart"  # 使用 ik_smart 进行搜索分词
                },
                "filename": {
                    "type": "keyword"
                },
                "file_type": {
                    "type": "keyword"
                },
                "url": {
                    "type": "keyword"
                },
                "date": {
                    "type": "date",  # 添加date字段
                    "format": "yyyy-MM-dd||yyyy-MM-dd HH:mm:ss||strict_date_optional_time||epoch_millis"
                },
                "upload_date": {
                    "type": "date"
                },
                "length": {
                    "type": "long"
                }
            }
        }

        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)

        self.es.indices.create(
            index=self.index_name,
            body={
                "settings": settings,
                "mappings": mappings
            }
        )

    def get_file_type(self, filename):
        """获取文件类型"""
        ext = os.path.splitext(filename)[1].lower()
        file_types = {
            '.pdf': 'pdf',
            '.xls': 'xls',
            '.xlsx': 'xls',
            '.doc': 'doc',
            '.docx': 'doc'
        }
        return file_types.get(ext, 'unknown')

    def extract_pdf_content(self, file_data):
        """提取PDF文档内容"""
        try:
            pdf_file = io.BytesIO(file_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            content = []
            for page in pdf_reader.pages:
                content.append(page.extract_text())
            return '\n'.join(content)
        except Exception as e:
            print(f"PDF提取错误: {str(e)}")
            return ""

    def extract_docx_content(self, file_data):
        """提取DOCX文档内容"""
        try:
            docx_file = io.BytesIO(file_data)
            doc = Document(docx_file)
            content = []
            for paragraph in doc.paragraphs:
                content.append(paragraph.text)
            return '\n'.join(content)
        except Exception as e:
            print(f"DOCX提取错误: {str(e)}")
            return ""

    def extract_doc_content(self, file_data):
        """提取DOC文档内容"""
        try:
            # 保存临时文件
            temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.doc').name
            with open(temp_path, 'wb') as temp_file:
                temp_file.write(file_data)

            # 使用Word COM对象打开文档
            word = win32com.client.Dispatch('Word.Application')
            word.Visible = False
            doc = word.Documents.Open(temp_path)
            content = doc.Content.Text

            # 清理
            doc.Close()
            word.Quit()
            os.unlink(temp_path)

            return content
        except Exception as e:
            print(f"DOC提取错误: {str(e)}")
            return ""
        finally:
            try:
                doc.Close()
                word.Quit()
            except:
                pass

    def extract_excel_content(self, file_data):
        """提取Excel文档内容"""
        try:
            excel_file = io.BytesIO(file_data)
            workbook = xlrd.open_workbook(file_contents=excel_file.read())
            content = []

            for sheet in workbook.sheets():
                sheet_content = []
                for row in range(sheet.nrows):
                    row_values = []
                    for col in range(sheet.ncols):
                        cell_value = sheet.cell_value(row, col)
                        if cell_value:
                            row_values.append(str(cell_value))
                    if row_values:
                        sheet_content.append(' '.join(row_values))
                content.append('\n'.join(sheet_content))

            return '\n\n'.join(content)
        except Exception as e:
            print(f"Excel提取错误: {str(e)}")
            return ""

    def extract_content(self, file_id, file_type):
        """根据文件类型提取内容"""
        try:
            # 从chunks获取文件数据
            file_data = self.get_file_data(file_id)
            if not file_data:
                return ""

            if file_type == 'pdf':
                return self.extract_pdf_content(file_data)
            elif file_type == 'doc':
                # 根据实际文件扩展名选择不同的提取方法
                if str(file_id).lower().endswith('.docx'):
                    return self.extract_docx_content(file_data)
                else:
                    return self.extract_doc_content(file_data)
            elif file_type == 'xls':
                return self.extract_excel_content(file_data)
            else:
                return ""
        except Exception as e:
            print(f"内容提取错误: {str(e)}")
            return ""

    def prepare_documents(self):
        """准备索引文档"""
        documents = []
        for doc in self.files_collection.find():
            filename = doc.get('filename', '')
            file_type = self.get_file_type(filename)

            # 提取文档内容
            content = self.extract_content(str(doc['_id']), file_type)

            doc_data = {
                "_id": str(doc['_id']),
                "filename": filename,
                "title": doc.get('title', filename),
                "url": doc.get('url', ''),
                "file_type": file_type,
                "date": doc.get('date', ''),  # 添加date字段
                "length": doc.get('length', 0),
                "content": content
            }
            documents.append(doc_data)
            print(f"已处理文档: {filename}")

        return documents

    def close(self):
        """关闭数据库连接"""
        self.mongo_client.close()
        try:
            pythoncom.CoUninitialize()
        except:
            pass


def main():
    indexer = DocumentIndexer(
        mongo_host='localhost',
        mongo_port=27017,
        mongo_db='nankai_news',
        es_host='localhost',
        es_port=9200,
        index_name='nankai_docs_index'
    )

    try:
        print("开始创建索引...")
        indexer.create_index()
        print("索引结构创建完成")

        print("开始准备文档...")
        documents = indexer.prepare_documents()
        print(f"文档准备完成，共 {len(documents)} 条记录")

        print("开始批量索引文档...")
        success, failed = bulk(
            indexer.es,
            [
                {
                    '_index': indexer.index_name,
                    '_id': doc['_id'],
                    **doc
                }
                for doc in documents
            ],
            refresh=True
        )
        print(f"文档索引完成，成功：{success} 条，失败：{failed} 条")

    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        indexer.close()


if __name__ == "__main__":
    main()