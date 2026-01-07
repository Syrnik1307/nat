import re
import logging
from datetime import datetime, timedelta
import pymorphy3
from django.db.models import Sum

logger = logging.getLogger(__name__)

class TranscriptService:
    def __init__(self):
        self.morph = pymorphy3.MorphAnalyzer()
        
    def parse_vtt(self, file_path):
        """Парсит VTT файл и возвращает список реплик"""
        entries = []
        
        # Regex для времени: 00:00:13.080 --> 00:00:15.510
        time_pattern = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            current_entry = {}
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line == 'WEBVTT':
                    continue
                
                # Поиск таймкодов
                time_match = time_pattern.match(line)
                if time_match:
                    start_str, end_str = time_match.groups()
                    current_entry['start'] = self._parse_time(start_str)
                    current_entry['end'] = self._parse_time(end_str)
                    current_entry['duration'] = (current_entry['end'] - current_entry['start']).total_seconds()
                    continue
                
                # Поиск текста (обычно строка после таймкода)
                # Формат Zoom: "Speaker Name: Code text"
                if 'start' in current_entry and ':' in line:
                    parts = line.split(':', 1)
                    speaker = parts[0].strip()
                    text = parts[1].strip()
                    
                    current_entry['speaker'] = speaker
                    current_entry['text'] = text
                    
                    entries.append(current_entry)
                    current_entry = {}
                    
        except Exception as e:
            logger.error(f"Error parsing VTT: {e}")
            return []
            
        return entries
        
    def _parse_time(self, time_str):
        # 00:00:01.050 -> inputs
        h, m, s = time_str.split(':')
        s, ms = s.split('.')
        return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))

    def analyze_transcript(self, file_path, lesson):
        """Анализирует транскрипт и возвращает статистику"""
        entries = self.parse_vtt(file_path)
        if not entries:
            return {}
            
        teacher = lesson.group.teacher
        students = list(lesson.group.students.all())
        
        # 1. Идентификация спикеров
        # Собираем уникальных спикеров из транскрипта
        unique_speakers = set(e.get('speaker', 'Unknown') for e in entries)
        
        # Маппинг: Speaker Name (VTT) -> Student (User Object) | 'teacher' | 'unknown'
        speaker_map = {}
        
        teacher_names = self._get_name_variants(teacher)
        
        # Маппинг студентов
        student_search_map = {}
        for s in students:
            # Варианты имени студента для поиска в именах спикеров
            variants = self._get_name_variants(s)
            student_search_map[s.id] = variants
        
        for speaker_name in unique_speakers:
            # Проверяем учителя
            if self._match_name(speaker_name, teacher_names):
                speaker_map[speaker_name] = {'type': 'teacher', 'id': teacher.id}
                continue
                
            # Проверяем студентов
            found_student = None
            for s_id, variants in student_search_map.items():
                if self._match_name(speaker_name, variants):
                    found_student = s_id
                    break
            
            if found_student:
                speaker_map[speaker_name] = {'type': 'student', 'id': found_student}
            else:
                speaker_map[speaker_name] = {'type': 'unknown', 'id': None}
                
        # 2. Расчет времени речи (Participation)
        stats_by_type = {'teacher': 0.0, 'student': 0.0, 'unknown': 0.0}
        stats_by_speaker = {}
        
        for entry in entries:
            speaker = entry.get('speaker', 'Unknown')
            duration = entry.get('duration', 0)
            
            mapping = speaker_map.get(speaker, {'type': 'unknown'})
            sType = mapping['type']
            stats_by_type[sType] += duration
            
            # Детализация по спикерам
            if speaker not in stats_by_speaker:
                stats_by_speaker[speaker] = {'duration': 0.0, 'type': sType}
            stats_by_speaker[speaker]['duration'] += duration

        total_duration = sum(stats_by_type.values())
        
        # 3. Упоминания имен учеников учителем
        mentions = {s.id: 0 for s in students}
        
        # Генерируем формы имен для поиска в тексте
        student_text_forms = {}
        for s in students:
            forms = set()
            # Базовое имя
            first_name = s.first_name
            if first_name:
                # Генерируем падежи для имени
                parsed = self.morph.parse(first_name)[0]
                for case in ['nomn', 'gent', 'datv', 'accs', 'ablt', 'loct', 'voct']:
                    form = parsed.inflect({case})
                    if form:
                        forms.add(form.word.lower())
            student_text_forms[s.id] = forms

        # Ищем упоминания только в речи учителя
        for entry in entries:
            speaker = entry.get('speaker', 'Unknown')
            mapping = speaker_map.get(speaker, {'type': 'unknown'})
            
            if mapping['type'] == 'teacher':
                text = entry.get('text', '').lower()
                for s_id, forms in student_text_forms.items():
                    # Простой поиск подстроки с границами слов
                    for form in forms:
                        if re.search(r'\b' + re.escape(form) + r'\b', text):
                            mentions[s_id] += 1
                            # Считаем одно упоминание на реплику достаточно? 
                            # Или хотим count? Для простоты break после первого нахождения имени в реплике
                            break 
                            
        # Сборка результата
        result = {
            'total_duration': total_duration,
            'stats_by_type': stats_by_type,
            'speakers': [
                {
                    'name': name,
                    'duration': data['duration'],
                    'percent': (data['duration'] / total_duration * 100) if total_duration > 0 else 0,
                    'type': data['type']
                }
                for name, data in stats_by_speaker.items()
            ],
            'mentions': [
                {
                    'student_id': s.id,
                    'student_name': s.get_full_name(),
                    'count': count
                }
                for s_id, count in mentions.items()
            ]
        }
        
        return result

    def _get_name_variants(self, user):
        """Возвращает список вариантов написания имени пользователя"""
        variants = set()
        if user.first_name:
            variants.add(user.first_name.lower())
        if user.last_name:
            variants.add(user.last_name.lower())
        if user.get_full_name():
            variants.add(user.get_full_name().lower())
            
        # Транслит? Zoom часто пишет транслитом "Ivan" вместо "Иван"
        # Пока опустим для простоты, т.к. требует библиотеки transliterate
        return list(variants)

    def _match_name(self, speaker_name, variants):
        """Проверяет, входит ли вариант имени в имя спикера"""
        speaker_lower = speaker_name.lower()
        for v in variants:
            if v in speaker_lower:
                return True
        return False
