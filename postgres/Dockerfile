FROM apache/age:latest

# Install pgvector extension (master branch supports PostgreSQL 18)
RUN apt-get update && apt-get install -y \
    postgresql-server-dev-18 \
    build-essential \
    git \
    && git clone https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector \
    && apt-get remove -y build-essential git postgresql-server-dev-18 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Use md5 auth instead of scram-sha-256 — SQLTools driver 0.5.6 has a bug with SCRAM on PG18
COPY pg_hba.conf /etc/postgresql/pg_hba.conf
