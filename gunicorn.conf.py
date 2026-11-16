import os
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 2          # SQLite: keep a small number of workers (single-writer database)
threads = 2
timeout = 60
accesslog = "-"
errorlog = "-"
