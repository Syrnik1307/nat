"""
KnowledgeService — поиск по базе знаний (RAG)

Отвечает за:
- Индексацию документов из docs/knowledge/
- Поиск релевантных чанков
- (Будущее) Embedding-based поиск с pgvector
"""

import logging
import os
import re
import hashlib
from pathlib import Path
from typing import List, Optional
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class KnowledgeService:
    """
    Сервис работы с базой знаний.
    
    Пока реализован простой keyword-based поиск.
    TODO: Добавить embedding-based поиск с pgvector.
    """
    
    # Путь к документам базы знаний
    KNOWLEDGE_DIR = 'docs/knowledge'
    
    # Размер чанка (приблизительно в символах)
    CHUNK_SIZE = 1500
    CHUNK_OVERLAP = 200
    
    @classmethod
    async def search(
        cls,
        query: str,
        language: str = 'ru',
        limit: int = 5,
    ) -> List[dict]:
        """
        Поиск релевантных чанков по запросу.
        
        Args:
            query: Поисковый запрос
            language: Язык (ru/en)
            limit: Максимум результатов
        
        Returns:
            List[dict]: Список чанков с метаданными
            [
                {
                    'doc_id': 1,
                    'chunk_id': 3,
                    'title': 'Как оплатить подписку',
                    'content': '...',
                    'score': 0.85,
                }
            ]
        """
        from ..models import KnowledgeChunk, KnowledgeDocument
        
        # Нормализуем запрос
        query_lower = query.lower()
        keywords = cls._extract_keywords(query_lower)
        
        if not keywords:
            return []
        
        # Простой поиск по ключевым словам
        # TODO: Заменить на embedding-based поиск
        
        chunks = await sync_to_async(list)(
            KnowledgeChunk.objects.select_related('document')
            .filter(document__is_active=True, document__language=language)
        )
        
        # Скоринг чанков
        scored_chunks = []
        for chunk in chunks:
            score = cls._calculate_relevance(chunk.content.lower(), keywords)
            if score > 0:
                scored_chunks.append({
                    'doc_id': chunk.document_id,
                    'chunk_id': chunk.id,
                    'title': chunk.document.title,
                    'section': chunk.section_title,
                    'content': chunk.content,
                    'score': score,
                })
        
        # Сортируем по релевантности
        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_chunks[:limit]
    
    @classmethod
    async def index_all_documents(cls) -> dict:
        """
        Переиндексировать все документы из KNOWLEDGE_DIR.
        
        Returns:
            dict: Статистика индексации
        """
        from ..models import KnowledgeDocument, KnowledgeChunk
        
        base_path = Path(settings.BASE_DIR).parent / cls.KNOWLEDGE_DIR
        
        if not base_path.exists():
            logger.warning(f"Knowledge directory not found: {base_path}")
            return {'error': f'Directory not found: {base_path}', 'indexed': 0}
        
        stats = {
            'indexed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
        }
        
        # Находим все .md файлы
        for md_file in base_path.rglob('*.md'):
            try:
                result = await cls._index_document(md_file, base_path)
                if result == 'indexed':
                    stats['indexed'] += 1
                elif result == 'updated':
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            except Exception as e:
                logger.error(f"Failed to index {md_file}: {e}")
                stats['errors'].append({'file': str(md_file), 'error': str(e)})
        
        logger.info(f"Knowledge base indexed: {stats}")
        return stats
    
    @classmethod
    async def _index_document(cls, file_path: Path, base_path: Path) -> str:
        """
        Индексировать один документ.
        
        Returns:
            'indexed' | 'updated' | 'skipped'
        """
        from ..models import KnowledgeDocument, KnowledgeChunk
        
        # Читаем файл
        content = file_path.read_text(encoding='utf-8')
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Относительный путь
        relative_path = str(file_path.relative_to(base_path.parent))
        
        # Проверяем, есть ли уже документ с таким путём
        doc = await sync_to_async(
            KnowledgeDocument.objects.filter(source_path=relative_path).first
        )()
        
        if doc:
            # Проверяем, изменился ли контент
            if doc.content_hash == content_hash:
                return 'skipped'
            
            # Удаляем старые чанки
            await sync_to_async(doc.chunks.all().delete)()
            doc.content_hash = content_hash
            doc.last_indexed_at = timezone.now()
            await sync_to_async(doc.save)()
            result = 'updated'
        else:
            # Создаём новый документ
            title = cls._extract_title(content, file_path.stem)
            category = cls._detect_category(relative_path)
            language = cls._detect_language(content)
            
            doc = await sync_to_async(KnowledgeDocument.objects.create)(
                source_path=relative_path,
                title=title,
                category=category,
                language=language,
                content_hash=content_hash,
                last_indexed_at=timezone.now(),
            )
            result = 'indexed'
        
        # Разбиваем на чанки
        chunks = cls._split_into_chunks(content)
        
        for i, (section_title, chunk_content) in enumerate(chunks):
            await sync_to_async(KnowledgeChunk.objects.create)(
                document=doc,
                chunk_index=i,
                content=chunk_content,
                section_title=section_title,
            )
        
        return result
    
    @classmethod
    def _extract_title(cls, content: str, fallback: str) -> str:
        """Извлечь заголовок из Markdown"""
        # Ищем первый # заголовок
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return fallback.replace('-', ' ').replace('_', ' ').title()
    
    @classmethod
    def _detect_category(cls, path: str) -> str:
        """Определить категорию по пути"""
        path_lower = path.lower()
        if 'faq' in path_lower:
            return 'faq'
        elif 'guide' in path_lower or 'how' in path_lower:
            return 'guide'
        elif 'error' in path_lower or 'troubleshoot' in path_lower:
            return 'troubleshooting'
        elif 'feature' in path_lower:
            return 'feature'
        elif 'policy' in path_lower or 'rule' in path_lower:
            return 'policy'
        return 'faq'
    
    @classmethod
    def _detect_language(cls, content: str) -> str:
        """Определить язык документа"""
        # Простая эвристика
        cyrillic = sum(1 for c in content[:1000] if '\u0400' <= c <= '\u04ff')
        latin = sum(1 for c in content[:1000] if 'a' <= c.lower() <= 'z')
        return 'ru' if cyrillic > latin else 'en'
    
    @classmethod
    def _split_into_chunks(cls, content: str) -> List[tuple]:
        """
        Разбить документ на чанки.
        
        Returns:
            List[tuple]: [(section_title, chunk_content), ...]
        """
        chunks = []
        
        # Разбиваем по секциям (## заголовки)
        sections = re.split(r'\n(?=##\s)', content)
        
        current_section = ''
        
        for section in sections:
            # Извлекаем заголовок секции
            title_match = re.match(r'^##\s+(.+)$', section, re.MULTILINE)
            if title_match:
                current_section = title_match.group(1).strip()
            
            # Если секция слишком большая — разбиваем дополнительно
            if len(section) > cls.CHUNK_SIZE:
                # Разбиваем по абзацам
                paragraphs = section.split('\n\n')
                current_chunk = ''
                
                for para in paragraphs:
                    if len(current_chunk) + len(para) < cls.CHUNK_SIZE:
                        current_chunk += para + '\n\n'
                    else:
                        if current_chunk.strip():
                            chunks.append((current_section, current_chunk.strip()))
                        current_chunk = para + '\n\n'
                
                if current_chunk.strip():
                    chunks.append((current_section, current_chunk.strip()))
            else:
                if section.strip():
                    chunks.append((current_section, section.strip()))
        
        return chunks
    
    @classmethod
    def _extract_keywords(cls, text: str) -> List[str]:
        """Извлечь ключевые слова из текста"""
        # Удаляем пунктуацию и разбиваем на слова
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Стоп-слова
        stopwords = {
            'и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'как', 'что', 'это',
            'не', 'а', 'но', 'или', 'мне', 'меня', 'мой', 'моя', 'мои', 'ты',
            'я', 'он', 'она', 'они', 'мы', 'вы', 'у', 'к', 'о', 'об', 'из',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
        }
        
        # Фильтруем короткие слова и стоп-слова
        keywords = [w for w in words if len(w) > 2 and w not in stopwords]
        
        return keywords
    
    @classmethod
    def _calculate_relevance(cls, text: str, keywords: List[str]) -> float:
        """Вычислить релевантность текста по ключевым словам"""
        if not keywords:
            return 0.0
        
        matches = sum(1 for kw in keywords if kw in text)
        
        # Нормализуем по количеству ключевых слов
        return matches / len(keywords)
