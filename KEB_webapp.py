#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KEB-App mit Schiebereglern – 8 Items (7-stufige Likert-Skala: 0 bis 6, Datum mit Zeit, Login/Registrierung)

Erholungs-Dimension:
  1) Körperliche Leistungsfähigkeit        (0 = am schlechtesten: rot, 6 = am besten: grün; 3 = neutral, gelb)
  2) Mentale Leistungsfähigkeit            (0 = schlecht, 6 = gut)
  3) Emotionale Ausgeglichenheit           (0 = schlecht, 6 = gut)
  4) Allgemeiner Erholungszustand          (0 = schlecht, 6 = gut)

Beanspruchungs-Dimension:
  5) Muskuläre Beanspruchung               (0 = am besten: grün, 6 = am schlechtesten: rot; 3 = neutral, gelb)
  6) Aktivierungsmangel                    (0 = gering, 6 = hoch)
  7) Emotionale Unausgeglichenheit         (0 = gering, 6 = hoch)
  8) Allgemeiner Beanspruchungszustand      (0 = gering, 6 = hoch)

- Wird nur das Datum (YYYY-MM-DD) eingegeben, wird automatisch die aktuelle Uhrzeit (HH:MM:SS) angehängt.
- Nach dem Speichern wird überprüft, ob die heutigen Subskalenwerte (basierend auf gegenüberliegenden Items)
  in mindestens einer Subskala um ≥ 2 Punkte unter dem 7-Tages-Durchschnitt liegen – es werden nur negative
  Veränderungen angezeigt.
- Zur Auswertung gibt es zwei Diagramme:
   1. Einzelitems: Zeitlicher Verlauf aller 8 Items.
   2. Subskalen: Gegenüberliegende Items werden zusammengefasst (Beanspruchungswerte werden mit "6 - Wert" invertiert).
- In beiden Diagrammen ist die Y-Achse fix von 0 bis 7 gesetzt.
- Jeder Benutzer hat über die Login-/Registrierungsfunktion seine eigenen Einträge.
- Zusätzlich gibt es einen Löschdialog, in dem Einträge selektiv gelöscht werden können.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import datetime
import matplotlib.pyplot as plt
import io
import base64
import os

app = Flask(__name__)
app.secret_key = "dein_geheimer_schluessel"  # Bitte als Environment Variable setzen
DB_FILE = "keb.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Tabelle für KEB-Einträge, jetzt mit user_id
    conn.execute("""
        CREATE TABLE IF NOT EXISTS keb (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT,
            k_leistung REAL,
            m_leistung REAL,
            e_ausgeg REAL,
            a_erhol REAL,
            musk_beans REAL,
            aktiv_mangel REAL,
            e_unausg REAL,
            a_beans REAL,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    # Tabelle für Benutzer
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route('/add', methods=["GET", "POST"])
def add_entry():
    if "user_id" not in session:
        flash("Bitte melde dich an.", "danger")
        return redirect(url_for("login"))
    if request.method == "POST":
        # Datum und Uhrzeit werden automatisch gesetzt:
        datum = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            k_leistung = float(request.form["k_leistung"])
            m_leistung = float(request.form["m_leistung"])
            e_ausgeg = float(request.form["e_ausgeg"])
            a_erhol = float(request.form["a_erhol"])
            musk_beans = float(request.form["musk_beans"])
            aktiv_mangel = float(request.form["aktiv_mangel"])
            e_unausg = float(request.form["e_unausg"])
            a_beans = float(request.form["a_beans"])
        except ValueError:
            flash("Bitte alle Werte als Zahl (zwischen 0 und 6) eingeben!", "danger")
            return redirect(url_for("add_entry"))
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO keb (datum, k_leistung, m_leistung, e_ausgeg, a_erhol,
                             musk_beans, aktiv_mangel, e_unausg, a_beans, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datum, k_leistung, m_leistung, e_ausgeg, a_erhol, musk_beans, aktiv_mangel, e_unausg, a_beans, session["user_id"]))
        conn.commit()
        conn.close()
        check_negative_deviation(datum, k_leistung, m_leistung, e_ausgeg, a_erhol, musk_beans, aktiv_mangel, e_unausg, a_beans)
        flash("Eintrag erfolgreich hinzugefügt!", "success")
        return redirect(url_for("index"))
    return render_template("add.html")


@app.route('/')
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    entries = conn.execute("SELECT * FROM keb WHERE user_id = ? ORDER BY datum DESC", (session["user_id"],)).fetchall()
    conn.close()
    return render_template("index.html", entries=entries)

@app.route('/add', methods=["GET", "POST"])
def add_entry():
    if "user_id" not in session:
        flash("Bitte melde dich an.", "danger")
        return redirect(url_for("login"))
    if request.method == "POST":
        datum = request.form["datum"].strip()
        # Falls nur Datum eingegeben (10 Zeichen), Uhrzeit anhängen
        if len(datum) == 10:
            datum = datum + " " + datetime.datetime.now().strftime("%H:%M:%S")
        try:
            datetime.datetime.strptime(datum, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            flash("Datum muss im Format YYYY-MM-DD oder YYYY-MM-DD HH:MM:SS sein!", "danger")
            return redirect(url_for("add_entry"))
        try:
            k_leistung = float(request.form["k_leistung"])
            m_leistung = float(request.form["m_leistung"])
            e_ausgeg = float(request.form["e_ausgeg"])
            a_erhol = float(request.form["a_erhol"])
            musk_beans = float(request.form["musk_beans"])
            aktiv_mangel = float(request.form["aktiv_mangel"])
            e_unausg = float(request.form["e_unausg"])
            a_beans = float(request.form["a_beans"])
        except ValueError:
            flash("Bitte alle Werte als Zahl (zwischen 0 und 6) eingeben!", "danger")
            return redirect(url_for("add_entry"))
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO keb (datum, k_leistung, m_leistung, e_ausgeg, a_erhol,
                             musk_beans, aktiv_mangel, e_unausg, a_beans, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (datum, k_leistung, m_leistung, e_ausgeg, a_erhol, musk_beans, aktiv_mangel, e_unausg, a_beans, session["user_id"]))
        conn.commit()
        conn.close()
        check_negative_deviation(datum, k_leistung, m_leistung, e_ausgeg, a_erhol, musk_beans, aktiv_mangel, e_unausg, a_beans)
        flash("Eintrag erfolgreich hinzugefügt!", "success")
        return redirect(url_for("index"))
    return render_template("add.html")

def check_negative_deviation(datum_str, k, m, e, a, mb, am, eu, ab):
    # Berechne heutige Subskalenwerte
    s1_today = (k + (6 - mb)) / 2
    s2_today = (m + (6 - am)) / 2
    s3_today = (e + (6 - eu)) / 2
    s4_today = (a + (6 - ab)) / 2
    today_subscales = [s1_today, s2_today, s3_today, s4_today]
    subscale_names = [
        "Subskala 1 (Körperl. / Musk. Beanspruchung)",
        "Subskala 2 (Mentale / Aktivierungsmangel)",
        "Subskala 3 (Emotionale Ausgeglichenheit / Emotionale Unausgeglichenheit)",
        "Subskala 4 (Allg. Erholungszustand / Allg. Beanspruchungszustand)"
    ]
    today_date = datetime.datetime.strptime(datum_str, "%Y-%m-%d %H:%M:%S").date()
    start_date = today_date - datetime.timedelta(days=7)
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT k_leistung, m_leistung, e_ausgeg, a_erhol,
               musk_beans, aktiv_mangel, e_unausg, a_beans
        FROM keb
        WHERE datum < ? AND datum >= ? AND user_id = ?
    """, (datum_str, start_date.strftime("%Y-%m-%d"), session["user_id"])).fetchall()
    conn.close()
    if not rows:
        return
    s1_list, s2_list, s3_list, s4_list = [], [], [], []
    for row in rows:
        k_val, m_val, e_val, a_val, mb_val, am_val, eu_val, ab_val = row
        s1 = (k_val + (6 - mb_val)) / 2
        s2 = (m_val + (6 - am_val)) / 2
        s3 = (e_val + (6 - eu_val)) / 2
        s4 = (a_val + (6 - ab_val)) / 2
        s1_list.append(s1)
        s2_list.append(s2)
        s3_list.append(s3)
        s4_list.append(s4)
    avg_s1 = sum(s1_list) / len(s1_list)
    avg_s2 = sum(s2_list) / len(s2_list)
    avg_s3 = sum(s3_list) / len(s3_list)
    avg_s4 = sum(s4_list) / len(s4_list)
    baseline = [avg_s1, avg_s2, avg_s3, avg_s4]
    messages = []
    for name, base, today_val in zip(subscale_names, baseline, today_subscales):
        if (base - today_val) >= 2:
            messages.append(f"{name}: heute {today_val:.1f} vs. 7-Tage-Durchschnitt {base:.1f}")
    if messages:
        flash("Negative Abweichungen festgestellt:<br>" + "<br>".join(messages), "warning")

@app.route('/plot_chart')
def plot_chart():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT datum, k_leistung, m_leistung, e_ausgeg, a_erhol,
               musk_beans, aktiv_mangel, e_unausg, a_beans
        FROM keb
        WHERE user_id = ?
        ORDER BY datum
    """, (session["user_id"],)).fetchall()
    conn.close()
    if not rows:
        flash("Keine Daten vorhanden.", "danger")
        return redirect(url_for("index"))
    dates, k_leistung, m_leistung, e_ausgeg, a_erhol = [], [], [], [], []
    musk_beans, aktiv_mangel, e_unausg, a_beans = [], [], [], []
    for row in rows:
        try:
            dt = datetime.datetime.strptime(row["datum"], "%Y-%m-%d %H:%M:%S")
        except:
            continue
        dates.append(dt)
        k_leistung.append(row["k_leistung"])
        m_leistung.append(row["m_leistung"])
        e_ausgeg.append(row["e_ausgeg"])
        a_erhol.append(row["a_erhol"])
        musk_beans.append(row["musk_beans"])
        aktiv_mangel.append(row["aktiv_mangel"])
        e_unausg.append(row["e_unausg"])
        a_beans.append(row["a_beans"])
    plt.figure(figsize=(10,6))
    plt.plot(dates, k_leistung, marker="o", label="Körperliche Leistungsfähigkeit")
    plt.plot(dates, m_leistung, marker="o", label="Mentale Leistungsfähigkeit")
    plt.plot(dates, e_ausgeg, marker="o", label="Emotionale Ausgeglichenheit")
    plt.plot(dates, a_erhol, marker="o", label="Allg. Erholungszustand")
    plt.plot(dates, musk_beans, marker="o", label="Muskuläre Beanspruchung")
    plt.plot(dates, aktiv_mangel, marker="o", label="Aktivierungsmangel")
    plt.plot(dates, e_unausg, marker="o", label="Emotionale Unausgeglichenheit")
    plt.plot(dates, a_beans, marker="o", label="Allg. Beanspruchungszustand")
    plt.xlabel("Datum und Zeit")
    plt.ylabel("Wert (0–6)")
    plt.title("KEB-Verlauf (Einzelitems)")
    plt.ylim(0,7)
    plt.xlim(dates[0], dates[-1])
    plt.gcf().autofmt_xdate()
    plt.legend(loc="best")
    plt.grid(True)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode("utf8")
    return render_template("plot.html", img_data=img_base64)

@app.route('/plot_subscales')
def plot_subscales():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT datum, k_leistung, m_leistung, e_ausgeg, a_erhol,
               musk_beans, aktiv_mangel, e_unausg, a_beans
        FROM keb
        WHERE user_id = ?
        ORDER BY datum
    """, (session["user_id"],)).fetchall()
    conn.close()
    if not rows:
        flash("Keine Daten vorhanden.", "danger")
        return redirect(url_for("index"))
    dates = []
    s1_list, s2_list, s3_list, s4_list = [], [], [], []
    for row in rows:
        try:
            dt = datetime.datetime.strptime(row["datum"], "%Y-%m-%d %H:%M:%S")
        except:
            continue
        dates.append(dt)
        k = row["k_leistung"]
        m = row["m_leistung"]
        e = row["e_ausgeg"]
        a = row["a_erhol"]
        mb = row["musk_beans"]
        am = row["aktiv_mangel"]
        eu = row["e_unausg"]
        ab = row["a_beans"]
        s1 = (k + (6 - mb)) / 2
        s2 = (m + (6 - am)) / 2
        s3 = (e + (6 - eu)) / 2
        s4 = (a + (6 - ab)) / 2
        s1_list.append(s1)
        s2_list.append(s2)
        s3_list.append(s3)
        s4_list.append(s4)
    plt.figure(figsize=(10,6))
    plt.plot(dates, s1_list, marker="o", label="Subskala 1 (Körperl. / Musk.)")
    plt.plot(dates, s2_list, marker="o", label="Subskala 2 (Mentale / Aktiv.)")
    plt.plot(dates, s3_list, marker="o", label="Subskala 3 (Emot. Ausgeg. / Emot. Unausgeg.)")
    plt.plot(dates, s4_list, marker="o", label="Subskala 4 (Allg. Erhol. / Allg. Beanspr.)")
    plt.xlabel("Datum und Zeit")
    plt.ylabel("Subskalenwert (0–6)")
    plt.title("KEB-Subskalenverlauf")
    plt.ylim(0,7)
    plt.xlim(dates[0], dates[-1])
    plt.gcf().autofmt_xdate()
    plt.legend(loc="best")
    plt.grid(True)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode("utf8")
    return render_template("plot.html", img_data=img_base64)

@app.route('/delete', methods=["GET", "POST"])
def delete_entries():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    if request.method == "POST":
        ids = request.form.getlist("delete")
        for entry_id in ids:
            conn.execute("DELETE FROM keb WHERE id = ? AND user_id = ?", (entry_id, session["user_id"]))
        conn.commit()
        conn.close()
        flash("Ausgewählte Einträge wurden gelöscht.", "success")
        return redirect(url_for("index"))
    else:
        entries = conn.execute("SELECT * FROM keb WHERE user_id = ? ORDER BY datum DESC", (session["user_id"],)).fetchall()
        conn.close()
        return render_template("delete.html", entries=entries)

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Erfolgreich angemeldet.", "success")
            return redirect(url_for("index"))
        else:
            flash("Ungültiger Benutzername oder Passwort.", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            flash("Bitte Benutzername und Passwort angeben.", "danger")
            return redirect(url_for("register"))
        hashed_pw = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Benutzername bereits vergeben.", "danger")
            conn.close()
            return redirect(url_for("register"))
        conn.close()
        flash("Registrierung erfolgreich! Bitte melde dich an.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("Erfolgreich abgemeldet.", "success")
    return redirect(url_for("login"))

if __name__ == '__main__':
    app.run(debug=True)
