#!/usr/bin/env python3
"""
Advanced Repository Analyzer for Elite Alpha Mirror Bot
Provides intelligent insights and optimization recommendations
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import ast
import re

class RepositoryAnalyzer:
    def __init__(self, repo_path="."):
        self.repo_path = Path(repo_path)
        self.analysis_results = {}
        self.file_stats = defaultdict(dict)
        self.code_metrics = defaultdict(dict)
        
    def analyze(self):
        """Run comprehensive repository analysis"""
        print("🔍 Elite Alpha Mirror Bot - Repository Analyzer")
        print("=" * 60)
        
        self.analyze_file_structure()
        self.analyze_code_quality()
        self.analyze_dependencies()
        self.analyze_configuration()
        self.analyze_security()
        self.analyze_performance()
        self.generate_recommendations()
        self.save_report()
        
        return self.analysis_results
    
    def analyze_file_structure(self):
        """Analyze repository file structure"""
        print("\n📁 Analyzing File Structure...")
        
        file_types = Counter()
        file_sizes = []
        duplicate_files = defaultdict(list)
        empty_files = []
        large_files = []
        
        for file_path in self.repo_path.rglob("*"):
            if file_path.is_file():
                # File type analysis
                suffix = file_path.suffix.lower() if file_path.suffix else 'no_extension'
                file_types[suffix] += 1
                
                # Size analysis
                size = file_path.stat().st_size
                file_sizes.append(size)
                
                if size == 0:
                    empty_files.append(str(file_path))
                elif size > 1024 * 1024:  # > 1MB
                    large_files.append((str(file_path), size))
                
                # Duplicate detection
                if size > 0:
                    try:
                        with open(file_path, 'rb') as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                            duplicate_files[file_hash].append(str(file_path))
                    except (PermissionError, OSError):
                        pass
        
        # Find actual duplicates
        duplicates = {h: files for h, files in duplicate_files.items() if len(files) > 1}
        
        self.analysis_results['file_structure'] = {
            'total_files': len(file_sizes),
            'file_types': dict(file_types.most_common()),
            'empty_files': empty_files,
            'large_files': sorted(large_files, key=lambda x: x[1], reverse=True)[:10],
            'duplicates': dict(duplicates),
            'total_size': sum(file_sizes),
            'avg_file_size': sum(file_sizes) / len(file_sizes) if file_sizes else 0
        }
        
        print(f"   Total files: {len(file_sizes)}")
        print(f"   File types: {len(file_types)}")
        print(f"   Empty files: {len(empty_files)}")
        print(f"   Duplicate groups: {len(duplicates)}")
    
    def analyze_code_quality(self):
        """Analyze Python code quality"""
        print("\n🐍 Analyzing Code Quality...")
        
        python_files = list(self.repo_path.rglob("*.py"))
        code_metrics = {
            'total_lines': 0,
            'comment_lines': 0,
            'blank_lines': 0,
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'complexity_issues': [],
            'style_issues': [],
            'documentation_coverage': 0
        }
        
        complexity_issues = []
        long_functions = []
        missing_docstrings = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                # Basic metrics
                code_metrics['total_lines'] += len(lines)
                code_metrics['comment_lines'] += sum(1 for line in lines if line.strip().startswith('#'))
                code_metrics['blank_lines'] += sum(1 for line in lines if not line.strip())
                
                # AST analysis
                try:
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            code_metrics['functions'] += 1
                            
                            # Check function length
                            func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                            if func_lines > 50:
                                long_functions.append(f"{py_file}:{node.name} ({func_lines} lines)")
                            
                            # Check for docstring
                            if not ast.get_docstring(node):
                                missing_docstrings.append(f"{py_file}:{node.name}")
                        
                        elif isinstance(node, ast.ClassDef):
                            code_metrics['classes'] += 1
                            if not ast.get_docstring(node):
                                missing_docstrings.append(f"{py_file}:{node.name}")
                        
                        elif isinstance(node, (ast.Import, ast.ImportFrom)):
                            code_metrics['imports'] += 1
                
                except SyntaxError as e:
                    complexity_issues.append(f"Syntax error in {py_file}: {e}")
                
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Calculate documentation coverage
        total_definitions = code_metrics['functions'] + code_metrics['classes']
        documented = total_definitions - len(missing_docstrings)
        code_metrics['documentation_coverage'] = (documented / total_definitions * 100) if total_definitions > 0 else 100
        
        code_metrics['long_functions'] = long_functions[:10]  # Top 10
        code_metrics['missing_docstrings'] = missing_docstrings[:20]  # Top 20
        
        self.analysis_results['code_quality'] = code_metrics
        
        print(f"   Python files: {len(python_files)}")
        print(f"   Total lines: {code_metrics['total_lines']:,}")
        print(f"   Functions: {code_metrics['functions']}")
        print(f"   Classes: {code_metrics['classes']}")
        print(f"   Documentation: {code_metrics['documentation_coverage']:.1f}%")
    
    def analyze_dependencies(self):
        """Analyze project dependencies"""
        print("\n📦 Analyzing Dependencies...")
        
        dependencies = {
            'requirements_files': [],
            'python_imports': Counter(),
            'unused_imports': [],
            'security_vulnerabilities': [],
            'outdated_packages': []
        }
        
        # Find requirements files
        req_files = list(self.repo_path.rglob("*requirements*.txt"))
        req_files.extend(list(self.repo_path.rglob("Pipfile")))
        req_files.extend(list(self.repo_path.rglob("pyproject.toml")))
        
        dependencies['requirements_files'] = [str(f) for f in req_files]
        
        # Analyze Python imports
        python_files = list(self.repo_path.rglob("*.py"))
        all_imports = set()
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract imports using regex
                import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+([^#\n]+)'
                imports = re.findall(import_pattern, content, re.MULTILINE)
                
                for from_module, import_items in imports:
                    module = from_module or import_items.split('.')[0].split(',')[0].strip()
                    if module and not module.startswith('.'):
                        dependencies['python_imports'][module] += 1
                        all_imports.add(module)
                
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Check for security issues (basic check)
        security_patterns = [
            (r'eval\s*\(', 'Use of eval() function'),
            (r'exec\s*\(', 'Use of exec() function'),
            (r'__import__\s*\(', 'Use of __import__() function'),
            (r'pickle\.loads?\s*\(', 'Use of pickle (potential security risk)'),
            (r'subprocess\.call\s*\(.*shell\s*=\s*True', 'Shell injection risk'),
        ]
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern, issue in security_patterns:
                    if re.search(pattern, content):
                        dependencies['security_vulnerabilities'].append(f"{py_file}: {issue}")
                        
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        self.analysis_results['dependencies'] = dependencies
        
        print(f"   Requirements files: {len(req_files)}")
        print(f"   Unique imports: {len(all_imports)}")
        print(f"   Security issues: {len(dependencies['security_vulnerabilities'])}")
    
    def analyze_configuration(self):
        """Analyze configuration files"""
        print("\n⚙️ Analyzing Configuration...")
        
        config_analysis = {
            'env_files': [],
            'config_files': [],
            'secrets_exposed': [],
            'missing_configs': [],
            'redundant_configs': []
        }
        
        # Find configuration files
        config_patterns = [
            "*.env*", "*.cfg", "*.ini", "*.yaml", "*.yml", "*.json",
            "config.*", "settings.*", "docker-compose.*"
        ]
        
        config_files = []
        for pattern in config_patterns:
            config_files.extend(self.repo_path.rglob(pattern))
        
        # Categorize config files
        for config_file in config_files:
            file_str = str(config_file)
            if '.env' in file_str:
                config_analysis['env_files'].append(file_str)
            else:
                config_analysis['config_files'].append(file_str)
        
        # Check for exposed secrets
        secret_patterns = [
            r'api[_-]?key\s*=\s*["\']?[a-zA-Z0-9]{20,}',
            r'secret[_-]?key\s*=\s*["\']?[a-zA-Z0-9]{20,}',
            r'password\s*=\s*["\']?[a-zA-Z0-9]{8,}',
            r'token\s*=\s*["\']?[a-zA-Z0-9]{20,}',
        ]
        
        for config_file in config_files:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in secret_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        config_analysis['secrets_exposed'].append(str(config_file))
                        break
                        
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Check for required configurations
        required_configs = [
            'ETH_WS_URL', 'ETH_HTTP_URL', 'ETHERSCAN_API_KEY',
            'OKX_API_KEY', 'DISCORD_WEBHOOK'
        ]
        
        env_content = ""
        env_files = [f for f in config_files if '.env' in str(f)]
        if env_files:
            try:
                with open(env_files[0], 'r', encoding='utf-8') as f:
                    env_content = f.read()
            except:
                pass
        
        for config in required_configs:
            if config not in env_content:
                config_analysis['missing_configs'].append(config)
        
        self.analysis_results['configuration'] = config_analysis
        
        print(f"   Configuration files: {len(config_files)}")
        print(f"   Environment files: {len(config_analysis['env_files'])}")
        print(f"   Missing configs: {len(config_analysis['missing_configs'])}")
        print(f"   Potential secrets: {len(config_analysis['secrets_exposed'])}")
    
    def analyze_security(self):
        """Analyze security aspects"""
        print("\n🔐 Analyzing Security...")
        
        security_analysis = {
            'hardcoded_secrets': [],
            'insecure_patterns': [],
            'file_permissions': [],
            'dependency_vulnerabilities': []
        }
        
        # Check for hardcoded secrets in Python files
        python_files = list(self.repo_path.rglob("*.py"))
        secret_patterns = [
            (r'api[_-]?key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', 'Hardcoded API key'),
            (r'password\s*=\s*["\'][^"\']{8,}["\']', 'Hardcoded password'),
            (r'secret\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', 'Hardcoded secret'),
            (r'0x[a-fA-F0-9]{40}', 'Ethereum address (potential private key)'),
        ]
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern, issue_type in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        security_analysis['hardcoded_secrets'].append(f"{py_file}: {issue_type}")
                        
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Check file permissions
        sensitive_files = list(self.repo_path.rglob("*.key"))
        sensitive_files.extend(list(self.repo_path.rglob("*.pem")))
        sensitive_files.extend(list(self.repo_path.rglob(".env*")))
        
        for sensitive_file in sensitive_files:
            try:
                stat = sensitive_file.stat()
                mode = oct(stat.st_mode)[-3:]
                if mode != '600' and mode != '644':
                    security_analysis['file_permissions'].append(f"{sensitive_file}: {mode}")
            except OSError:
                continue
        
        self.analysis_results['security'] = security_analysis
        
        print(f"   Hardcoded secrets: {len(security_analysis['hardcoded_secrets'])}")
        print(f"   Permission issues: {len(security_analysis['file_permissions'])}")
    
    def analyze_performance(self):
        """Analyze performance aspects"""
        print("\n⚡ Analyzing Performance...")
        
        performance_analysis = {
            'large_files': [],
            'inefficient_patterns': [],
            'blocking_operations': [],
            'optimization_opportunities': []
        }
        
        # Find large files that might impact performance
        large_files = []
        for file_path in self.repo_path.rglob("*"):
            if file_path.is_file():
                size = file_path.stat().st_size
                if size > 1024 * 1024:  # > 1MB
                    large_files.append((str(file_path), size))
        
        performance_analysis['large_files'] = sorted(large_files, key=lambda x: x[1], reverse=True)[:10]
        
        # Check Python files for performance issues
        python_files = list(self.repo_path.rglob("*.py"))
        inefficient_patterns = [
            (r'\.append\(.+\)\s*for\s+.+\s+in\s+', 'List comprehension opportunity'),
            (r'for\s+.+\s+in\s+range\(len\(.+\)\):', 'Use enumerate() instead'),
            (r'time\.sleep\(', 'Blocking sleep operation'),
            (r'requests\.get\(', 'Synchronous HTTP request'),
            (r'open\(.+\)\.read\(\)', 'File not properly closed'),
        ]
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern, issue in inefficient_patterns:
                    if re.search(pattern, content):
                        performance_analysis['inefficient_patterns'].append(f"{py_file}: {issue}")
                        
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        self.analysis_results['performance'] = performance_analysis
        
        print(f"   Large files: {len(large_files)}")
        print(f"   Inefficient patterns: {len(performance_analysis['inefficient_patterns'])}")
    
    def generate_recommendations(self):
        """Generate optimization recommendations"""
        print("\n💡 Generating Recommendations...")
        
        recommendations = []
        
        # File structure recommendations
        file_data = self.analysis_results.get('file_structure', {})
        if file_data.get('empty_files'):
            recommendations.append({
                'category': 'cleanup',
                'priority': 'high',
                'action': f"Remove {len(file_data['empty_files'])} empty files",
                'impact': 'Reduces clutter and improves organization'
            })
        
        if file_data.get('duplicates'):
            dup_count = sum(len(files) - 1 for files in file_data['duplicates'].values())
            recommendations.append({
                'category': 'optimization',
                'priority': 'medium',
                'action': f"Remove {dup_count} duplicate files",
                'impact': 'Saves disk space and reduces confusion'
            })
        
        # Code quality recommendations
        code_data = self.analysis_results.get('code_quality', {})
        if code_data.get('documentation_coverage', 100) < 70:
            recommendations.append({
                'category': 'documentation',
                'priority': 'medium',
                'action': f"Improve documentation coverage from {code_data['documentation_coverage']:.1f}% to 80%+",
                'impact': 'Better maintainability and understanding'
            })
        
        if code_data.get('long_functions'):
            recommendations.append({
                'category': 'refactoring',
                'priority': 'low',
                'action': f"Refactor {len(code_data['long_functions'])} long functions",
                'impact': 'Improved code readability and maintainability'
            })
        
        # Security recommendations
        security_data = self.analysis_results.get('security', {})
        if security_data.get('hardcoded_secrets'):
            recommendations.append({
                'category': 'security',
                'priority': 'critical',
                'action': f"Move {len(security_data['hardcoded_secrets'])} hardcoded secrets to environment variables",
                'impact': 'Critical security improvement'
            })
        
        # Configuration recommendations
        config_data = self.analysis_results.get('configuration', {})
        if len(config_data.get('env_files', [])) > 1:
            recommendations.append({
                'category': 'configuration',
                'priority': 'medium',
                'action': f"Consolidate {len(config_data['env_files'])} environment files into one",
                'impact': 'Simplified configuration management'
            })
        
        # Performance recommendations
        perf_data = self.analysis_results.get('performance', {})
        if perf_data.get('inefficient_patterns'):
            recommendations.append({
                'category': 'performance',
                'priority': 'medium',
                'action': f"Optimize {len(perf_data['inefficient_patterns'])} inefficient code patterns",
                'impact': 'Improved application performance'
            })
        
        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 4))
        
        self.analysis_results['recommendations'] = recommendations
        
        print(f"   Generated {len(recommendations)} recommendations")
        
        # Print top recommendations
        for i, rec in enumerate(recommendations[:5], 1):
            priority_icon = {'critical': '🚨', 'high': '🔴', 'medium': '🟡', 'low': '🔵'}.get(rec['priority'], '⚪')
            print(f"   {i}. {priority_icon} [{rec['category'].upper()}] {rec['action']}")
    
    def save_report(self):
        """Save analysis report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.repo_path / f"analysis_report_{timestamp}.json"
        
        # Add metadata
        self.analysis_results['metadata'] = {
            'timestamp': timestamp,
            'analyzer_version': '2.0',
            'repository_path': str(self.repo_path),
            'total_recommendations': len(self.analysis_results.get('recommendations', []))
        }
        
        with open(report_file, 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)
        
        print(f"\n📄 Analysis report saved: {report_file}")
        
        # Create summary report
        self.create_summary_report(report_file.with_suffix('.md'))
    
    def create_summary_report(self, output_file):
        """Create human-readable summary report"""
        with open(output_file, 'w') as f:
            f.write("# Elite Alpha Mirror Bot - Repository Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Executive Summary
            f.write("## 📊 Executive Summary\n\n")
            file_data = self.analysis_results.get('file_structure', {})
            code_data = self.analysis_results.get('code_quality', {})
            
            f.write(f"- **Total Files:** {file_data.get('total_files', 0):,}\n")
            f.write(f"- **Total Size:** {file_data.get('total_size', 0) / (1024*1024):.1f} MB\n")
            f.write(f"- **Code Lines:** {code_data.get('total_lines', 0):,}\n")
            f.write(f"- **Functions:** {code_data.get('functions', 0)}\n")
            f.write(f"- **Classes:** {code_data.get('classes', 0)}\n")
            f.write(f"- **Documentation:** {code_data.get('documentation_coverage', 0):.1f}%\n\n")
            
            # Top Recommendations
            f.write("## 🎯 Top Recommendations\n\n")
            recommendations = self.analysis_results.get('recommendations', [])
            for i, rec in enumerate(recommendations[:10], 1):
                priority_icon = {'critical': '🚨', 'high': '🔴', 'medium': '🟡', 'low': '🔵'}.get(rec['priority'], '⚪')
                f.write(f"{i}. {priority_icon} **{rec['category'].title()}** - {rec['action']}\n")
                f.write(f"   - *Impact:* {rec['impact']}\n\n")
            
            # File Structure
            f.write("## 📁 File Structure Analysis\n\n")
            if file_data.get('file_types'):
                f.write("### File Types\n")
                for ext, count in list(file_data['file_types'].items())[:10]:
                    f.write(f"- **{ext}:** {count} files\n")
                f.write("\n")
            
            # Security Issues
            security_data = self.analysis_results.get('security', {})
            if security_data.get('hardcoded_secrets'):
                f.write("## 🔐 Security Issues\n\n")
                f.write("### Hardcoded Secrets Found\n")
                for issue in security_data['hardcoded_secrets'][:5]:
                    f.write(f"- {issue}\n")
                f.write("\n")
            
            # Performance Issues
            perf_data = self.analysis_results.get('performance', {})
            if perf_data.get('large_files'):
                f.write("## ⚡ Performance Analysis\n\n")
                f.write("### Large Files\n")
                for file_path, size in perf_data['large_files'][:5]:
                    f.write(f"- **{file_path}:** {size / (1024*1024):.1f} MB\n")
                f.write("\n")
            
            f.write("---\n")
            f.write("*Report generated by Elite Alpha Mirror Bot Repository Analyzer*\n")
        
        print(f"📄 Summary report saved: {output_file}")

def main():
    """Main entry point"""
    analyzer = RepositoryAnalyzer()
    results = analyzer.analyze()
    
    print(f"\n✅ Analysis complete!")
    print(f"📊 Found {len(results.get('recommendations', []))} optimization opportunities")
    
    # Quick recommendations summary
    recommendations = results.get('recommendations', [])
    if recommendations:
        print(f"\n🎯 Top 3 Recommendations:")
        for i, rec in enumerate(recommendations[:3], 1):
            priority_icon = {'critical': '🚨', 'high': '🔴', 'medium': '🟡', 'low': '🔵'}.get(rec['priority'], '⚪')
            print(f"   {i}. {priority_icon} {rec['action']}")

if __name__ == "__main__":
    main()