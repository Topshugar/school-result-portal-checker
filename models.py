import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class School(db.Model):
    __tablename__ = "schools"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Integer, nullable=False, default=0)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    students = db.relationship("Student", backref="school", lazy=True, cascade="all, delete-orphan")
    pins = db.relationship("Pin", backref="school", lazy=True, cascade="all, delete-orphan")


class Student(db.Model):
    __tablename__ = "students"
    __table_args__ = (db.UniqueConstraint("school_id", "reg_number", name="uq_student_school_reg"),)

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    reg_number = db.Column(db.String(100), nullable=False, index=True)
    full_name = db.Column(db.String(160), nullable=False)
    class_name = db.Column(db.String(100), nullable=False)
    results = db.relationship("Result", backref="student", lazy=True, cascade="all, delete-orphan")


class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = db.Column(db.String(120), nullable=False)
    ca1 = db.Column(db.Float, nullable=False, default=0)
    ca2 = db.Column(db.Float, nullable=False, default=0)
    exam = db.Column(db.Float, nullable=False, default=0)
    total = db.Column(db.Float, nullable=False, default=0)


class Pin(db.Model):
    __tablename__ = "pins"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    is_paid = db.Column(db.Boolean, nullable=False, default=False)
    is_used = db.Column(db.Boolean, nullable=False, default=False)
    # Used to make Paystack verification idempotent if a parent refreshes the callback.
    payment_reference = db.Column(db.String(255), unique=True, nullable=True)
