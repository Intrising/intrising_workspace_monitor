#!/usr/bin/env python3
"""
反饋分析器 - 用於從用戶反饋中學習並改進評分系統
實現完整的反饋學習循環
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter
import anthropic
import os


class FeedbackAnalyzer:
    """分析用戶反饋並提取學習見解"""

    def __init__(self, database, anthropic_api_key: str = None):
        """
        初始化反饋分析器

        Args:
            database: TaskDatabase 實例
            anthropic_api_key: Anthropic API key (可選)
        """
        self.db = database
        self.logger = logging.getLogger("FeedbackAnalyzer")

        # 初始化 Anthropic client（用於分析反饋文本）
        api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None
            self.logger.warning("未提供 Anthropic API key，將使用規則基礎的分析")

        # 預定義的反饋關鍵詞模式
        self.feedback_patterns = {
            'too_harsh': [
                '太嚴格', '太嚴厲', '評分太低', '過於苛刻', 'too harsh', 'too strict',
                '不公平', '太苛刻', '太低了', '評太低'
            ],
            'too_lenient': [
                '太寬鬆', '太寬容', '評分太高', '過於寬容', 'too lenient', 'too generous',
                '太高了', '評太高', '不夠嚴格'
            ],
            'missed_issue': [
                '沒注意到', '忽略了', '漏掉了', '沒發現', 'missed', 'overlooked',
                '應該指出', '未提及', '沒提到'
            ],
            'incorrect_assessment': [
                '評估錯誤', '理解錯誤', '誤解', '不正確', 'incorrect', 'wrong assessment',
                '評估不當', '判斷錯誤'
            ],
            'good_feedback': [
                '準確', '中肯', '很好', '有幫助', 'accurate', 'helpful', 'spot on',
                '很有用', '精準', '到位'
            ],
            'format_issue': [
                '格式', 'format', '排版', 'formatting', '標題', 'title'
            ],
            'content_issue': [
                '內容', 'content', '完整性', 'completeness', '詳細', 'detail'
            ],
            'clarity_issue': [
                '清晰', 'clarity', '表達', 'expression', '理解', 'understanding'
            ],
            'actionability_issue': [
                '可操作', 'actionable', '具體', 'specific', '步驟', 'steps'
            ]
        }

    def analyze_feedback_text(self, feedback_text: str, score_data: Dict) -> Dict:
        """
        使用 Claude 分析單條反饋文本

        Args:
            feedback_text: 用戶反饋文本
            score_data: 原始評分數據

        Returns:
            分析結果字典
        """
        if not self.client or not feedback_text.strip():
            # 回退到規則基礎分析
            return self._rule_based_analysis(feedback_text, score_data)

        try:
            # 使用 Claude 深度分析反饋
            prompt = f"""請分析以下用戶對 AI 評分系統的反饋，提取關鍵信息：

## 原始評分信息
- 格式分數: {score_data.get('format_score', 'N/A')}/100
- 內容分數: {score_data.get('content_score', 'N/A')}/100
- 清晰度分數: {score_data.get('clarity_score', 'N/A')}/100
- 可操作性分數: {score_data.get('actionability_score', 'N/A')}/100
- 總分: {score_data.get('overall_score', 'N/A')}/100

## 用戶反饋
{feedback_text}

請以 JSON 格式回答以下問題：
1. sentiment: 反饋情緒（positive/negative/neutral）
2. feedback_type: 反饋類型（too_harsh/too_lenient/missed_issue/incorrect_assessment/good_feedback）
3. affected_dimension: 主要涉及的評分維度（format/content/clarity/actionability/overall/null）
4. specific_issue: 用戶指出的具體問題（1-2句話總結）
5. suggested_score_adjustment: 建議的分數調整（+10/-5等，如果用戶沒有明確建議則為null）
6. key_learning: 從這條反饋中應該學習的關鍵點（1句話）

請只返回 JSON，不要其他文字。"""

            message = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = message.content[0].text.strip()

            # 提取 JSON（處理可能的 markdown 代碼塊）
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()

            analysis = json.loads(result_text)
            self.logger.info(f"Claude 分析反饋完成: {analysis.get('feedback_type')}")
            return analysis

        except Exception as e:
            self.logger.error(f"Claude 分析反饋失敗，回退到規則分析: {e}")
            return self._rule_based_analysis(feedback_text, score_data)

    def _rule_based_analysis(self, feedback_text: str, score_data: Dict) -> Dict:
        """
        基於規則的反饋分析（當 Claude API 不可用時使用）

        Args:
            feedback_text: 用戶反饋文本
            score_data: 原始評分數據

        Returns:
            分析結果字典
        """
        text_lower = feedback_text.lower()

        # 判斷情緒
        sentiment = 'neutral'
        if any(kw in text_lower for kw in self.feedback_patterns['good_feedback']):
            sentiment = 'positive'
        elif any(kw in text_lower for kw in
                 self.feedback_patterns['too_harsh'] +
                 self.feedback_patterns['too_lenient'] +
                 self.feedback_patterns['missed_issue'] +
                 self.feedback_patterns['incorrect_assessment']):
            sentiment = 'negative'

        # 判斷反饋類型
        feedback_type = 'neutral'
        for ftype, keywords in self.feedback_patterns.items():
            if ftype in ['good_feedback', 'format_issue', 'content_issue',
                        'clarity_issue', 'actionability_issue']:
                continue
            if any(kw in text_lower for kw in keywords):
                feedback_type = ftype
                break

        # 判斷涉及的維度
        affected_dimension = None
        for dimension in ['format', 'content', 'clarity', 'actionability']:
            if any(kw in text_lower for kw in self.feedback_patterns[f'{dimension}_issue']):
                affected_dimension = dimension
                break

        # 提取分數調整建議（簡單的數字模式匹配）
        score_adjustment = None
        score_patterns = [
            r'應該.*?(\d+)',
            r'至少.*?(\d+)',
            r'給.*?(\d+)',
            r'(\d+)\s*分'
        ]
        for pattern in score_patterns:
            match = re.search(pattern, feedback_text)
            if match:
                suggested_score = int(match.group(1))
                current_score = score_data.get('overall_score', 0)
                if current_score and suggested_score != current_score:
                    score_adjustment = suggested_score - current_score
                    break

        return {
            'sentiment': sentiment,
            'feedback_type': feedback_type,
            'affected_dimension': affected_dimension,
            'specific_issue': feedback_text[:100],  # 取前100字
            'suggested_score_adjustment': score_adjustment,
            'key_learning': f"用戶認為{feedback_type}於{affected_dimension or '整體評分'}"
        }

    def process_new_feedback(self, score_id: str, feedback_text: str) -> bool:
        """
        處理新的用戶反饋，分析並更新模式庫

        Args:
            score_id: 評分記錄 ID
            feedback_text: 用戶反饋文本

        Returns:
            是否處理成功
        """
        try:
            # 獲取評分記錄
            score_record = self.db.get_score_record(score_id)
            if not score_record:
                self.logger.error(f"找不到評分記錄: {score_id}")
                return False

            # 分析反饋
            analysis = self.analyze_feedback_text(feedback_text, score_record)

            # 更新或創建反饋模式
            self._update_feedback_pattern(analysis, score_record, feedback_text)

            self.logger.info(f"反饋處理完成: {score_id}, 類型={analysis['feedback_type']}")
            return True

        except Exception as e:
            self.logger.error(f"處理反饋失敗: {e}", exc_info=True)
            return False

    def _update_feedback_pattern(self, analysis: Dict, score_record: Dict,
                                  feedback_text: str) -> None:
        """
        更新反饋模式數據庫

        Args:
            analysis: 分析結果
            score_record: 評分記錄
            feedback_text: 原始反饋文本
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                # 生成模式 ID（基於類型和維度）
                dimension = analysis.get('affected_dimension') or 'general'
                feedback_type = analysis['feedback_type']
                pattern_id = f"{feedback_type}:{dimension}"

                # 查詢現有模式
                cursor.execute("""
                    SELECT * FROM feedback_patterns WHERE pattern_id = ?
                """, (pattern_id,))

                existing = cursor.fetchone()
                now = datetime.now().isoformat()

                if existing:
                    # 更新現有模式
                    occurrence_count = existing['occurrence_count'] + 1

                    # 合併示例反饋（保留最多5個）
                    example_feedbacks = json.loads(existing['example_feedbacks'] or '[]')
                    example_feedbacks.append(feedback_text[:200])
                    example_feedbacks = example_feedbacks[-5:]  # 只保留最新5個

                    # 更新平均分數偏差
                    avg_deviation = existing['avg_score_deviation'] or 0
                    if analysis.get('suggested_score_adjustment'):
                        new_deviation = analysis['suggested_score_adjustment']
                        avg_deviation = (avg_deviation * (occurrence_count - 1) + new_deviation) / occurrence_count

                    cursor.execute("""
                        UPDATE feedback_patterns
                        SET occurrence_count = ?,
                            avg_score_deviation = ?,
                            example_feedbacks = ?,
                            last_seen = ?,
                            updated_at = ?
                        WHERE pattern_id = ?
                    """, (
                        occurrence_count,
                        avg_deviation,
                        json.dumps(example_feedbacks, ensure_ascii=False),
                        now,
                        now,
                        pattern_id
                    ))
                else:
                    # 創建新模式
                    cursor.execute("""
                        INSERT INTO feedback_patterns (
                            pattern_id, pattern_type, dimension, feedback_theme,
                            occurrence_count, avg_score_deviation, example_feedbacks,
                            identified_issue, suggested_adjustment,
                            last_seen, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pattern_id,
                        feedback_type,
                        dimension,
                        analysis.get('key_learning', ''),
                        1,
                        analysis.get('suggested_score_adjustment'),
                        json.dumps([feedback_text[:200]], ensure_ascii=False),
                        analysis.get('specific_issue', ''),
                        f"考慮調整{dimension}評分標準" if dimension != 'general' else '檢討整體評分標準',
                        now,
                        now,
                        now
                    ))

                conn.commit()
                self.logger.info(f"反饋模式已更新: {pattern_id}")

        except Exception as e:
            self.logger.error(f"更新反饋模式失敗: {e}", exc_info=True)

    def get_feedback_insights(self, days: int = 30, min_occurrences: int = 2) -> Dict:
        """
        獲取反饋學習見解（用於注入到 prompt 中）

        Args:
            days: 查看最近幾天的反饋
            min_occurrences: 最小出現次數閾值

        Returns:
            反饋見解字典
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

                # 查詢高頻反饋模式
                cursor.execute("""
                    SELECT * FROM feedback_patterns
                    WHERE last_seen >= ? AND occurrence_count >= ?
                    ORDER BY occurrence_count DESC
                    LIMIT 10
                """, (cutoff_date, min_occurrences))

                patterns = cursor.fetchall()

                # 查詢實際的反饋總數
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM issue_scores
                    WHERE user_feedback IS NOT NULL
                    AND user_feedback != ''
                    AND created_at >= ?
                """, (cutoff_date,))
                total_feedbacks = cursor.fetchone()['total']

                if not patterns:
                    return {
                        'has_insights': False,
                        'summary': f'最近 {days} 天收到 {total_feedbacks} 條用戶反饋，尚未識別出重複模式',
                        'adjustments': []
                    }

                # 構建見解
                insights = {
                    'has_insights': True,
                    'summary': f"最近 {days} 天收到 {total_feedbacks} 條用戶反饋，識別出 {len(patterns)} 個反饋模式",
                    'top_issues': [],
                    'dimension_adjustments': {},
                    'general_guidance': []
                }

                for pattern in patterns:
                    issue_desc = f"{pattern['feedback_theme']} (出現 {pattern['occurrence_count']} 次)"
                    insights['top_issues'].append(issue_desc)

                    # 維度特定的調整建議
                    dimension = pattern['dimension']
                    if dimension and dimension != 'general':
                        if dimension not in insights['dimension_adjustments']:
                            insights['dimension_adjustments'][dimension] = []

                        adjustment = {
                            'issue': pattern['identified_issue'],
                            'suggestion': pattern['suggested_adjustment'],
                            'avg_deviation': pattern['avg_score_deviation']
                        }
                        insights['dimension_adjustments'][dimension].append(adjustment)

                    # 通用指導
                    if pattern['pattern_type'] == 'too_harsh':
                        insights['general_guidance'].append(
                            f"⚠️ 用戶反映{dimension or '整體'}評分過於嚴格，考慮適度放寬標準"
                        )
                    elif pattern['pattern_type'] == 'too_lenient':
                        insights['general_guidance'].append(
                            f"⚠️ 用戶反映{dimension or '整體'}評分過於寬鬆，考慮提高要求"
                        )
                    elif pattern['pattern_type'] == 'missed_issue':
                        insights['general_guidance'].append(
                            f"⚠️ 用戶指出遺漏了{dimension or '某些'}問題，加強該方面的檢查"
                        )

                return insights

        except Exception as e:
            self.logger.error(f"獲取反饋見解失敗: {e}", exc_info=True)
            return {
                'has_insights': False,
                'summary': '獲取反饋數據時發生錯誤',
                'adjustments': []
            }

    def create_feedback_snapshot(self) -> Optional[str]:
        """
        創建反饋快照（定期執行，用於追蹤改進趨勢）

        Returns:
            快照 ID，如果失敗則返回 None
        """
        try:
            # 獲取最近 30 天的所有反饋
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()

                # 統計反饋數量和情緒
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        user_feedback
                    FROM issue_scores
                    WHERE user_feedback IS NOT NULL
                    AND user_feedback != ''
                    AND created_at >= ?
                """, (cutoff_date,))

                feedbacks = cursor.fetchall()
                total_feedbacks = len(feedbacks)

                if total_feedbacks == 0:
                    self.logger.info("沒有新反饋，跳過快照創建")
                    return None

                # 簡單的情緒統計（可以改進為使用 Claude 分析）
                positive = 0
                negative = 0
                neutral = 0

                for fb in feedbacks:
                    text = (fb['user_feedback'] or '').lower()
                    if any(kw in text for kw in self.feedback_patterns['good_feedback']):
                        positive += 1
                    elif any(kw in text for kw in
                            self.feedback_patterns['too_harsh'] +
                            self.feedback_patterns['too_lenient']):
                        negative += 1
                    else:
                        neutral += 1

                # 獲取 top issues
                insights = self.get_feedback_insights(days=30, min_occurrences=2)

                # 創建快照
                snapshot_id = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                now = datetime.now().isoformat()

                cursor.execute("""
                    INSERT INTO feedback_snapshots (
                        snapshot_id, snapshot_date, total_feedbacks,
                        positive_count, negative_count, neutral_count,
                        top_issues, learning_insights, prompt_adjustments,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot_id,
                    datetime.now().date().isoformat(),
                    total_feedbacks,
                    positive,
                    negative,
                    neutral,
                    json.dumps(insights.get('top_issues', []), ensure_ascii=False),
                    json.dumps(insights, ensure_ascii=False),
                    json.dumps(insights.get('general_guidance', []), ensure_ascii=False),
                    now
                ))

                conn.commit()
                self.logger.info(f"反饋快照已創建: {snapshot_id}")
                return snapshot_id

        except Exception as e:
            self.logger.error(f"創建反饋快照失敗: {e}", exc_info=True)
            return None

    def get_feedback_statistics(self, days: int = 30) -> Dict:
        """
        獲取反饋統計數據（用於 UI 展示）

        Args:
            days: 統計最近幾天的數據

        Returns:
            統計數據字典
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()

                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

                # 總反饋數
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM issue_scores
                    WHERE user_feedback IS NOT NULL
                    AND user_feedback != ''
                    AND created_at >= ?
                """, (cutoff_date,))

                total = cursor.fetchone()['total']

                # 模式統計
                cursor.execute("""
                    SELECT pattern_type, dimension, SUM(occurrence_count) as count
                    FROM feedback_patterns
                    WHERE last_seen >= ?
                    GROUP BY pattern_type, dimension
                    ORDER BY count DESC
                """, (cutoff_date,))

                patterns = cursor.fetchall()

                # 最近快照
                cursor.execute("""
                    SELECT * FROM feedback_snapshots
                    ORDER BY snapshot_date DESC
                    LIMIT 5
                """)

                recent_snapshots = cursor.fetchall()

                return {
                    'total_feedbacks': total,
                    'date_range': f"最近 {days} 天",
                    'patterns': [dict(p) for p in patterns],
                    'recent_snapshots': [dict(s) for s in recent_snapshots],
                    'insights': self.get_feedback_insights(days=days)
                }

        except Exception as e:
            self.logger.error(f"獲取反饋統計失敗: {e}", exc_info=True)
            return {
                'total_feedbacks': 0,
                'patterns': [],
                'recent_snapshots': [],
                'error': str(e)
            }
