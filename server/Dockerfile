FROM python:3.11-slim

# Install system dependencies including ODBC drivers
RUN apt-get update && apt-get install -y \
    curl \
    autoconf \
    automake \
    libtool \
    pkg-config \
    git \
    build-essential \
    gnupg \
    unixodbc \
    unixodbc-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver 17 for SQL Server
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    rm -rf /var/lib/apt/lists/*

# Build and install libpostal
WORKDIR /tmp
RUN git clone https://github.com/openvenues/libpostal && \
    cd libpostal && \
    ./bootstrap.sh && \
    ./configure --datadir=/usr/local/share/libpostal && \
    make -j4 && \
    make install && \
    ldconfig && \
    cd / && \
    rm -rf /tmp/libpostal

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
# Install requirements excluding Windows-only packages (pywin32 is for email processing on Windows host)
RUN grep -v "pywin32" requirements.txt > requirements-linux.txt && \
    pip install --no-cache-dir -r requirements-linux.txt && \
    pip install postal && \
    rm requirements-linux.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
