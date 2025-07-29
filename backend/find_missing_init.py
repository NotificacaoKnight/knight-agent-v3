#!/usr/bin/env python3
import os

dirs_with_py = set()
for root, dirs, files in os.walk('.'):
    if 'venv' in root or '__pycache__' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            dirs_with_py.add(root)

print("🔍 Procurando diretórios com arquivos .py mas sem __init__.py:\n")

for dir_path in sorted(dirs_with_py):
    init_file = os.path.join(dir_path, '__init__.py')
    if not os.path.exists(init_file) and dir_path != '.':
        print(f'❌ Faltando: {init_file}')
        py_files = [f for f in os.listdir(dir_path) if f.endswith('.py')]
        print(f'   Arquivos .py: {py_files[:3]}')
        print()

print("✅ Verificação completa!")