#!/usr/bin/env python3
# validate_setup.py
"""
Script de validation pour vérifier que tous les composants
sont correctement configurés avant de lancer les tests.
"""

import sys
import os
import importlib.util
from pathlib import Path


def check_file_exists(file_path, description):
    """Vérifie qu'un fichier existe."""
    if Path(file_path).exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description} MANQUANT: {file_path}")
        return False


def check_import(module_name, description):
    """Vérifie qu'un module peut être importé."""
    try:
        __import__(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description} ERREUR: {module_name} - {e}")
        return False


def check_config_validity():
    """Vérifie la validité de la configuration."""
    try:
        from config.enhanced_production_config import get_config, validate_environment_config

        environments = ["development", "staging", "production", "load_testing"]
        all_valid = True

        print("\n🔧 Validation des configurations:")
        for env in environments:
            is_valid = validate_environment_config(env)
            status = "✅ Valide" if is_valid else "❌ Invalide"
            print(f"   {env}: {status}")
            if not is_valid:
                all_valid = False

        return all_valid

    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        return False


def main():
    """Fonction principale de validation."""
    print("🔍 VALIDATION DE LA CONFIGURATION DU PROJET")
    print("=" * 50)

    all_checks_passed = True

    # 1. Vérification des fichiers essentiels
    print("\n📁 Vérification des fichiers essentiels:")

    essential_files = [
        ("system_launcher.py", "SystemLauncher principal"),
        ("config/enhanced_production_config.py", "Configuration de production"),
        ("tests/performance/direct_test_adapter.py", "DirectTestAdapter"),
        ("tests/performance/run_all_scenarios.py", "Script principal des tests"),
        ("tests/performance/scenarios/performance_scenarios.py", "Gestionnaire de scénarios"),
        ("tests/performance/constant_load_test.py", "Test de charge constante"),
        ("tests/performance/increasing_load_test.py", "Test de charge croissante"),
        ("tests/performance/burst_load_test.py", "Test de pic de charge"),
        ("tests/performance/dependency_test.py", "Test de dépendances"),
        ("dashboard/app.py", "Application dashboard"),
    ]

    for file_path, description in essential_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False

    # 2. Vérification des imports Python
    print("\n🐍 Vérification des imports Python:")

    python_modules = [
        ("asyncio", "Asyncio (standard)"),
        ("logging", "Logging (standard)"),
        ("json", "JSON (standard)"),
        ("time", "Time (standard)"),
        ("threading", "Threading (standard)"),
        ("pathlib", "Pathlib (standard)"),
        ("datetime", "Datetime (standard)"),
        ("collections", "Collections (standard)"),
        ("argparse", "Argparse (standard)"),
    ]

    for module_name, description in python_modules:
        if not check_import(module_name, description):
            all_checks_passed = False

    # 3. Vérification des dépendances optionnelles
    print("\n📦 Vérification des dépendances optionnelles:")

    optional_modules = [
        ("spade", "SPADE (multi-agents)"),
        ("flask", "Flask (dashboard web)"),
        ("numpy", "NumPy (calculs)"),
        ("matplotlib", "Matplotlib (graphiques)"),
    ]

    for module_name, description in optional_modules:
        try:
            __import__(module_name)
            print(f"✅ {description}: {module_name}")
        except ImportError:
            print(f"⚠️  {description} OPTIONNEL: {module_name} (non requis)")

    # 4. Vérification de la configuration
    if not check_config_validity():
        all_checks_passed = False

    # 5. Création des répertoires nécessaires
    print("\n📂 Création des répertoires nécessaires:")

    directories = [
        "logs",
        "logs/performance",
        "logs/scenarios",
        "tests/performance/scenarios",
        "reports",
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Répertoire créé/vérifié: {directory}")

    # 6. Test de création d'un fichier de test
    print("\n🧪 Test d'écriture de fichiers:")

    try:
        test_file = Path("logs/test_validation.txt")
        test_file.write_text(f"Test de validation - {Path.cwd()}")
        test_file.unlink()  # Supprimer le fichier de test
        print("✅ Écriture de fichiers: OK")
    except Exception as e:
        print(f"❌ Écriture de fichiers: ERREUR - {e}")
        all_checks_passed = False

    # 7. Résumé final
    print("\n" + "=" * 50)
    if all_checks_passed:
        print("🎉 VALIDATION RÉUSSIE!")
        print("✅ Tous les composants sont prêts")
        print("🚀 Vous pouvez lancer les tests avec:")
        print("   python tests/performance/run_all_scenarios.py --all")
        return 0
    else:
        print("❌ VALIDATION ÉCHOUÉE!")
        print("🔧 Veuillez corriger les erreurs ci-dessus avant de continuer")
        print("\n💡 Actions recommandées:")
        print("   1. Vérifiez que tous les fichiers sont présents")
        print("   2. Installez les dépendances manquantes")
        print("   3. Corrigez les erreurs de configuration")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)