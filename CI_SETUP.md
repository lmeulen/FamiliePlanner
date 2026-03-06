# CI/CD Pipeline Setup

Deze repository heeft een GitHub Actions CI/CD pipeline die automatisch draait bij elke push en pull request.

## Pipeline Overzicht

De CI pipeline bestaat uit de volgende checks:

### 1. **Python Linting (Ruff)**
- Controleert Python code op style issues en potentiële bugs
- Gebruikt moderne, snelle Ruff linter
- Controleert ook code formatting

**Lokaal uitvoeren:**
```bash
pip install ruff==0.8.5
ruff check .
ruff format --check .
```

**Auto-fix:**
```bash
ruff check --fix .
ruff format .
```

### 2. **Python Formatting (Black)**
- Controleert of Python code consistent geformatteerd is
- Gebruikt Black code formatter

**Lokaal uitvoeren:**
```bash
pip install black==24.10.0
black --check .
```

**Auto-format:**
```bash
black .
```

### 3. **Type Checking (mypy)**
- Controleert type hints in Python code
- Helpt bugs vroeg te detecteren

**Lokaal uitvoeren:**
```bash
pip install mypy==1.14.0
mypy app/ --ignore-missing-imports
```

### 4. **Python Tests (pytest)**
- Draait alle unit en integration tests
- Gebruikt pytest met async support

**Lokaal uitvoeren:**
```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

### 5. **Commit Message Linting**
- Controleert of commit messages voldoen aan conventional commits
- Draait alleen bij pull requests

**Commit message formaat:**
```
<type>: <subject>

[optional body]

[optional footer]
```

**Types:**
- `feat`: Nieuwe feature
- `fix`: Bug fix
- `docs`: Documentatie wijziging
- `style`: Code style wijziging (formatting, etc)
- `refactor`: Code refactoring
- `perf`: Performance verbetering
- `test`: Test toevoegingen/wijzigingen
- `chore`: Build/dependency wijzigingen
- `ci`: CI/CD configuratie
- `build`: Build system wijzigingen
- `revert`: Revert van eerdere commit

**Voorbeelden:**
```bash
git commit -m "feat: Add calendar export functionality"
git commit -m "fix: Resolve timezone issue in event display"
git commit -m "docs: Update API documentation"
```

## Configuratie Bestanden

- **pyproject.toml**: Python tooling configuratie (ruff, black, mypy, pytest)
- **commitlint.config.js**: Commit message linting configuratie
- **package.json**: Node.js dependencies voor commitlint
- **.github/workflows/ci.yml**: GitHub Actions workflow definitie

## Pre-commit Hooks (Optioneel)

Je kunt pre-commit hooks instellen om lokaal automatisch checks uit te voeren:

```bash
pip install pre-commit
```

Maak `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.5
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/psf/black
    rev: 24.10.0
    hooks:
      - id: black
```

Activeer:
```bash
pre-commit install
```

## Troubleshooting

### Ruff format issues
Als Ruff format check faalt:
```bash
ruff format .
git add -u
git commit --amend --no-edit
```

### Type checking errors
Mypy errors kunnen vaak opgelost worden door:
- Type hints toevoegen
- `# type: ignore` comments gebruiken waar nodig
- Dependencies updaten

### Commit message issues
Bij foute commit messages:
```bash
git commit --amend -m "feat: Correct commit message"
```

## Status Badge

Voeg dit toe aan je README om de CI status te tonen:

```markdown
![CI Pipeline](https://github.com/USERNAME/REPO/actions/workflows/ci.yml/badge.svg)
```

## Ontwikkel Workflow

1. **Voor elke commit:**
   ```bash
   # Run linting en formatting
   ruff check --fix .
   ruff format .
   black .

   # Run tests
   pytest tests/
   ```

2. **Voor elke push:**
   - GitHub Actions draait automatisch alle checks
   - Controleer de Actions tab op GitHub voor resultaten

3. **Voor pull requests:**
   - Alle checks moeten slagen voordat mergen
   - Commit messages worden gecontroleerd
   - Reviewers kunnen de code checken

## Lokale Development Setup

```bash
# Python dependencies
pip install -r requirements.txt
pip install ruff black mypy pytest pytest-asyncio

# JavaScript dependencies (voor commitlint)
npm install

# Run alle checks
ruff check .
black --check .
mypy app/ --ignore-missing-imports
pytest tests/
```
