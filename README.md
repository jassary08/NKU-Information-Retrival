# 信息检索系统期末设计

## 基于南开大学新闻的搜索引擎

###### 2212039 田晋宇 物联网工程

[git仓库：https://github.com/jassary08/NKU-Information-Retrival](https://github.com/jassary08/NKU-Information-Retrival)

## 一、项目简介

![image-20241217142253759](.\images\image-20241217142253759.png)

本项目是南开大学**24fall信息检索系统**的期末设计，基于**南开大学新闻及南开大学各大学院网站**的新闻数据构建的搜索引擎。前端采用**React 18.2**用于构建用户界面组件，**Tailwind CSS**实现响应式设计和样式管理，后端采用**Flask**框架构建**RESTful API**，搜索引擎采用开源的分布式搜索和分析引擎**elasticsearch**，最终实现了**站内查询**，**短语查询**，**通配查询**等基础查询功能，**用户个性化推荐**，**搜索建议**等个性化查询功能。

## 二、项目概览

```
Data_creating/
Index_creating/
├── Elasticsearch_Doc_Index.py
└── Elasticsearch_Index.py
main_web/
├── app/
├── config.py
└── run.py
Page_rank/
└── script.py
Spider/
├── config.py
├── database.py
├── parser.py
└── scraper.py
```

- **Data_creating：**用于对爬取的数据集进行**清洗**，包括删除重复数据，删除无对应新闻的网页快照等。
- **Index_creating：**使用**Elasticsearch**构建文本索引。
- **main_web：**构建**web页面**，同时建立**flask服务器**作为后端响应。
- **Page_rank：**用于计算爬取到的新闻url的**PageRank**。
- **Spider：**爬取南开大学新闻网的新闻数据。

## 三、项目内容

### 数据爬取

![image-20241217144924193](.\images\image-20241217144924193.png)

本搜索引擎的数据来自**南开大学新闻网及南开大学各大学院网站**，以下是数据明细：

- **南开大学新闻网：93568条**
- **南开大学信息公开网：1657条**
- **南开大学商学院：1087条**
- **南开大学周恩来政府管理学院：1107条**
- **南开大学历史学院：875条**
- **南开大学物理科学学院：865条**
- **南开大学金融学院：561条**
- **南开大学经济学院：1119条**

在新闻数据爬取的过程中我们还获取了网页中的**附件下载链接**用于构建**文档查询**共**1372条**。

对于**新闻数据**爬取的数据格式如下：

![image-20241217144645918](.\images\image-20241217144645918.png)

![image-20241217144823729](.\images\image-20241217144823729.png)

对于文档数据我们将**文档链接**与**文档内容**（以二进制形式存储）分开存储：

![image-20241217154917090](.\images\image-20241217154917090.png)

![image-20241217155001584](.\images\image-20241217155001584.png)

### 文本索引

索引的构建采用**Elasticsearch**的索引构建功能，首先使用**Elasticsearch**官方提供的**ik分词器**和**pinyin分词器**，方便用户查询时自动补全，对各个字段进行索引：

```python
        settings = {
            "index": {
                "number_of_replicas": 2,
                "number_of_shards": 1
            },
            "analysis": {
                "analyzer": {
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
                        "limit_first_letter_length":  16,
                        "remove_duplicated_term": True
                    }
                }
            }
        }

        mappings = {
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                    "search_analyzer": "ik_smart",
                    "fields": {
                        "suggest": {
                            "type": "completion",
                            "analyzer": "ik_smart_pinyin",
                            "search_analyzer": "ik_smart_pinyin",
                            "preserve_separators": True,
                            "preserve_position_increments": True,
                            "max_input_length": 50
                        },
                    }
                },
                "url": {"type": "keyword"},
                "content": {
                    "type": "text",
                    "analyzer": "ik_max_word",
                    "search_analyzer": "ik_smart"
                },
                "source": {"type": "keyword"},
                "date": {"type": "date", "format": "yyyy-MM-dd"}
            }
        }

```

![image-20241217162755995](.\images\image-20241217162755995.png)

对于文档查询，我们为其构建了单独的索引：

```python
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
                        "analyzer": "ik_max_word",  
                        "search_analyzer": "ik_smart",  
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
                        "analyzer": "ik_max_word",  
                        "search_analyzer": "ik_smart" 
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
                        "type": "date",  
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
```

### 链接分析

我们对爬取的每一条新闻链接进行了链接分析，计算PageRank得分最终存入mongo数据库，具体的算法在`/Page_rank/script.py`：

![image-20241217163027237](.\images\image-20241217163027237.png)

在进行查询操作时，我们会根据**url**从**mongo数据库**中查询对应url的**PageRank**分数，并赋予一定的权重，同时加入了时间衰减因子：

```python
            "functions": [
                {
                    "exp": {
                        "date": {
                            "origin": "now", 
                            "scale": "180d",
                            "decay": 0.5,
                            "offset": "7d"
                        }
                    },
                    "weight": 0.3
                },
                {
                    "script_score": {
                        "script": {
                            "source": "coalesce(doc['pagerank_score'].value, 0.0) * params.weight",
                            "params": {
                                "weight": 0.2
                            }
                        }
                    }
                }
            ]
```

### 查询服务

#### 1. 站内查询

**站内查询**是指用户在站内搜索新闻内容或文档的常规查询。它的核心逻辑基于 `multi_match` 查询。

```python
"multi_match": {
    "query": query,
    "fields": ["title^3", "title.autocomplete^2", "content"],
    "type": "best_fields",
    "operator": "and",
    "fuzziness": "AUTO"
}
```

搜索时支持对**时间**和**发布媒体**的筛选：

![image-20241217170533660](.\images\image-20241217170533660.png)

#### 2. 文档查询

**文档查询**专门用于搜索结构化文档，例如 PDF、Word 文档等。`search_documents` 方法实现了这一功能，通过 `multi_match` 查询在多个字段中搜索指定关键词：

```python
"multi_match": {
    "query": query,
    "fields": ["title^4", "content", "filename"],
    "type": "best_fields",
    "operator": "and"
}
```

选择文档查询功能后,允许用户**筛选文件类型**：

![image-20241217185022954](.\images\image-20241217185022954.png)

#### 3. 短语查询

**短语查询**用于精确匹配短语，控制词序和相对距离。在代码中的具体实现为，如果 `query_type` 为 `phrase`，使用 `match_phrase` 查询。

```python
"bool": {
    "should": [
        {
            "match_phrase": {
                "title": {
                    "query": query,
                    "slop": 0,
                    "boost": 3.0
                }
            }
        },
        {
            "match_phrase": {
                "content": {
                    "query": query,
                    "slop": 0,
                    "boost": 1.0
                }
            }
        }
    ],
    "minimum_should_match": 2
}

```

例如我们搜索**南开大学举办**时，**普通查询**可能会搜索到**南开大学举办**或者**举办南开大学**等信息，而使用短语查询之后，只会搜索到南开大学举办相关词条：

![image-20241217173023662](.\images\image-20241217173023662.png)

#### 4. 通配查询

**通配查询**允许用户使用特殊字符 `*` 和 `?` 来进行灵活的模式匹配搜索：

```python
   search_body["query"]["function_score"]["query"]["bool"]["must"].extend([
                    {
                        "bool": {
                            "should": [
                                {
                                    "wildcard": {
                                        "title": {
                                            "value": query,
                                            "boost": 3
                                        }
                                    }
                                },
                                {
                                    "wildcard": {
                                        "content": {
                                            "value": query
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ])
```

- `*` 可以匹配0个或多个任意字符。例如，搜索**"*时报"**可以匹配**"环球时报"**、**"中国经济时报"**、**"证券时报"**等结果。

  ![image-20241217182938898](.\images\image-20241217182938898.png)

- `?` 精确匹配一个字符。例如，搜索**"????时报"**只会匹配**"中国经济时报"**这样开头是四个字的结果，而不会匹配**"环球时报"**。

  ![image-20241217183032466](.\images\image-20241217183032466.png)

#### 5. 查询日志

该搜索引擎实现了用户登录功能，支持**用户注册**，**用户登录**，**历史记录**的查询,用户的星系存储在mongo数据库中：

![image-20241217173858319](.\images\image-20241217173858319.png)

![image-20241217173803492](.\images\image-20241217173803492.png)

#### 6. 网页快照

网页快照是搜索引擎为用户提供的一种辅助功能，它将网页在某个时间点的内容**保存**下来，以便用户可以在原始网页不可访问或加载缓慢时查看网页内容的**历史版本**。

当搜索引擎返回用户搜索结果时，每一条记录都会带有网页快照标识，用户点击即可查看该网页的历史版本：

![image-20241217174539866](.\images\image-20241217174539866.png)



![image-20241217174647009](.\images\image-20241217174647009.png)

#### 7. 个性化查询

**个性化查询**查询是通过普通搜索结果结合用户的**偏好关键词**，提升某些结果的排名。

用户偏好通过 `top_keywords` 动态注入到查询中，并使用 `should` 子句提高与偏好关键词匹配文档的分数：

```python
if user_preferences:
    if user_preferences.get('top_keywords'):
        search_body["query"]["function_score"]["query"]["bool"]["should"] = [
            {
                "match": {
                    "content": {
                        "query": keyword,
                        "boost": 0.1
                    }
                }
            }
            for keyword in user_preferences['top_keywords']
        ]
```

例如某个用户比较关注**金融学院**的新闻，那么在搜索**南开大学**时系统会自动推荐南开大学金融学院相关的新闻：

![image-20241217174216872](.\images\image-20241217174216872.png)

![image-20241217174101799](.\images\image-20241217174101799.png)

### Web界面

**web界面**参考了**google**的搜索界面的设计里面融入了一些自己的小巧思，结合了用户认证、搜索建议、历史查询记录以及结果分页等功能。使用了 **HTML**、**CSS**、**React** 和 **Vanilla JavaScript** 技术，配合 **TailwindCSS** 展现出各种不同的样式：

![image-20241217175421809](.\images\image-20241217175421809.png)

![image-20241217175443977](.\images\image-20241217175443977.png)

以及一些**UI动画**上的一些小细节，例如搜索框：

![image-20241217175559443](.\images\image-20241217175559443.png)

![image-20241217175713212](.\images\image-20241217175713212.png)

### 个性化推荐 

**个性化推荐**部分我实现的是用户搜索输入时的联想建议，支持对拼音的联想推荐。

用户在搜索框中输入前缀时，系统会提供实时的搜索建议。主要依赖于 **Elasticsearch** 的 `completion suggester` 特性，同时支持模糊匹配以容错拼写错误：

```python
suggest_body = {
    "_source": ["title", "source", "url"],
    "suggest": {
        "title-suggest": {
            "prefix": prefix,
            "completion": {
                "field": "title.suggest",
                "size": 10,
                "skip_duplicates": True,
                "fuzzy": {
                    "fuzziness": "AUTO",
                    "prefix_length": 1
                }
            }
        }
    }
}
```

当用户输入**nankai**时，下方会自动展示十条来你想搜索，点击后会自动跳转搜索结果：

![image-20241217180818447](.\images\image-20241217180818447.png)

![image-20241217180914435](.\images\image-20241217180914435.png)
