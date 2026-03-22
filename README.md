
# DASS Assignment 2

## Git Repository

https://github.com/Shardul0007/Dass_Ass2.git

## Prerequisites

- Python 3.x
- (For blackbox tests) Docker Desktop / Docker Engine

## Setup (one-time)

From the `Dass_Ass2` folder:

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install -U pip
python -m pip install pytest requests
```

## How to run the code (MoneyPoly)

```powershell
python .\whitebox\code\main.py
```

## How to run the tests

### Whitebox tests

```powershell
python -m pytest -q .\whitebox\tests
```

### Integration tests

```powershell
python -m pytest -q .\integration\tests
```

### Blackbox tests (QuickCart API)

1) Start the QuickCart server (port `8080`):

```powershell
docker run --rm -p 8080:8080 quickcart
```

2) In a second terminal, run the blackbox tests:

```powershell
$env:QUICKCART_BASE_URL = "http://localhost:8080"
$env:QUICKCART_ROLL_NUMBER = "2024101077" 
python -m pytest -q .\blackbox\tests
```
