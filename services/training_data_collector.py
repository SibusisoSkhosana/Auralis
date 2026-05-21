import json
import os
from pathlib import Path

from models.entities import Feedback, OutputResult, User


data_dir = Path('data')
data_dir.mkdir(parents=True, exist_ok=True)


class TrainingDataCollectorService:
    def __init__(self, db_session):
        self.db_session = db_session

    def collect_approved_samples(self):
        approved_feedback = (
            self.db_session.query(Feedback)
            .join(OutputResult)
            .join(User)
            .filter(Feedback.choice.in_(['a', 'b', 'tie']), User.consent_to_training.is_(True))
            .all()
        )

        approved_rows = []
        for feedback in approved_feedback:
            result = feedback.result
            if result is None:
                continue
            approved_rows.append({
                'result_id': result.id,
                'mix_a_path': result.mix_a_path,
                'mix_b_path': result.mix_b_path,
                'feedback_choice': feedback.choice,
                'recorded_at': feedback.recorded_at.isoformat(),
            })

        return approved_rows

    def separate_raw_vs_approved(self):
        raw_results = (
            self.db_session.query(OutputResult)
            .outerjoin(Feedback)
            .filter(~OutputResult.approved_for_training)
            .all()
        )

        raw_files = [
            {
                'result_id': result.id,
                'mix_a_path': result.mix_a_path,
                'mix_b_path': result.mix_b_path,
                'created_at': result.created_at.isoformat(),
            }
            for result in raw_results
        ]

        approved_files = self.collect_approved_samples()
        return {'raw': raw_files, 'approved': approved_files}

    def mark_sample_for_training(self, output_result):
        if output_result is None:
            return False

        output_result.approved_for_training = True
        self.db_session.add(output_result)
        self.db_session.commit()
        return True

    def export_training_lists(self):
        separated = self.separate_raw_vs_approved()
        raw_path = data_dir / 'raw_training_files.jsonl'
        approved_path = data_dir / 'approved_training_files.jsonl'

        with open(raw_path, 'w', encoding='utf-8') as raw_file:
            for row in separated['raw']:
                raw_file.write(json.dumps(row) + '\n')

        with open(approved_path, 'w', encoding='utf-8') as approved_file:
            for row in separated['approved']:
                approved_file.write(json.dumps(row) + '\n')

        return {'raw': str(raw_path), 'approved': str(approved_path)}
