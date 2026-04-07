from typing import List, Tuple
import logging

import torch
from langchain_core.documents import Document
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

class BgeV2M3Reranker:
    """Rerank candidate documents using BAAI/bge-reranker-v2-m3 model."""

    def __init__(self, timeout: float = 30.0) -> None:
        """
        Initialize tokenizer and model.

        Args:
            timeout (float): Placeholder for compatibility, currently unused
        """
        self._model_name: str = "BAAI/bge-reranker-v2-m3"
        self._timeout: float = timeout

        # 加载 tokenizer 和模型
        self._tokenizer: AutoTokenizer = AutoTokenizer.from_pretrained(self._model_name)
        self._model: AutoModelForSequenceClassification = AutoModelForSequenceClassification.from_pretrained(
            self._model_name
        )
        self._model.eval()
        self._device: torch.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if self._device == "cpu":
            logger.warning("CUDA is unavailable in this device, now is using CPU!")
        self._model.to(self._device)

    async def rerank(self, query: str, documents: List[Document], max_length: int = 1024) -> List[Document]:
        """
        Rerank a list of Document objects based on relevance to the query.

        Args:
            query (str): The query string
            documents (List[Document]): List of candidate documents
            max_length (int): Maximum token length for tokenizer

        Returns:
            List[Document]: Documents sorted by relevance (highest first)
        """
        # 构造 query-doc 对列表
        pairs: List[List[str]] = [[query, doc.page_content] for doc in documents]

        # tokenizer 批量编码
        inputs: dict[str, torch.Tensor] = self._tokenizer(
            pairs,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=max_length,
        )

        # 移动到模型设备
        for key in inputs:
            inputs[key] = inputs[key].to(self._device)

        # 推理得到 logits
        with torch.no_grad():
            logits: torch.Tensor = self._model(**inputs, return_dict=True).logits.view(-1).float()

        # 映射到 0-1
        scores: torch.Tensor = torch.sigmoid(logits)

        # 文档和分数打包并排序
        doc_scores: List[Tuple[Document, float]] = list(zip(documents, scores.tolist()))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # 返回排序后的文档列表
        sorted_docs: List[Document] = [doc for doc, _ in doc_scores]
        return sorted_docs