from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

from models.database import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    consent_to_training = db.Column(db.Boolean, default=False, nullable=False)

    uploads = db.relationship('AudioUpload', back_populates='user', lazy='dynamic')
    sessions = db.relationship('ProcessingSession', back_populates='user', lazy='dynamic')
    feedbacks = db.relationship('Feedback', back_populates='user', lazy='dynamic')

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class AudioUpload(db.Model):
    __tablename__ = 'audio_uploads'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('processing_sessions.id', ondelete='CASCADE'), nullable=True)
    original_name = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=True)
    size = db.Column(db.Integer, nullable=False)
    path = db.Column(db.String(1024), nullable=False)
    status = db.Column(db.String(80), default='saved', nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='uploads')
    session = db.relationship('ProcessingSession', back_populates='uploads')


class ProcessingSession(db.Model):
    __tablename__ = 'processing_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(80), default='pending', nullable=False)
    model_confidence = db.Column(db.Float, nullable=True)

    user = db.relationship('User', back_populates='sessions')
    uploads = db.relationship('AudioUpload', back_populates='session', lazy='dynamic')
    output_result = db.relationship('OutputResult', back_populates='session', uselist=False)


class OutputResult(db.Model):
    __tablename__ = 'output_results'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('processing_sessions.id', ondelete='CASCADE'), nullable=False)
    mix_a_path = db.Column(db.String(1024), nullable=False)
    mix_b_path = db.Column(db.String(1024), nullable=False)
    params_a = db.Column(db.JSON, nullable=False)
    params_b = db.Column(db.JSON, nullable=False)
    validation_a = db.Column(db.JSON, nullable=True)
    validation_b = db.Column(db.JSON, nullable=True)
    both_valid = db.Column(db.Boolean, default=False, nullable=False)
    approved_for_training = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    session = db.relationship('ProcessingSession', back_populates='output_result')
    feedback = db.relationship('Feedback', back_populates='result', lazy='dynamic')


class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    result_id = db.Column(db.Integer, db.ForeignKey('output_results.id', ondelete='CASCADE'), nullable=False)
    choice = db.Column(db.String(20), nullable=False)
    meta = db.Column(db.JSON, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', back_populates='feedbacks')
    result = db.relationship('OutputResult', back_populates='feedback')
