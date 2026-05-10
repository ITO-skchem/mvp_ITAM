"""컴포넌트 마스터 표준 시드 (CVE 분석 가능 표기 기준).

* alias 입력은 order.txt 96~138 라인을 따른다.
* 예시(C# → C# language + .NET Framework framework + .NET runtime)에 따라 각 alias가
  실제 CVE 분석에서 함께 추적되는 platform/runtime을 페어링하여 자동 생성한다.
* CPE 2.3 표기는 NVD CPE Dictionary 명명 관례를 따르며, NVD에 직접 항목이 없는
  언어/사양(HTML, JavaScript 명세, VB.NET, XML, Lotusscript, Formula, C++, MFC,
  classic VB 등)은 cpe_name을 빈 값으로 둔다 (CMDB 카탈로그 용도).
* EOS/EOL 날짜는 각 벤더 공식 발표(가능한 범위)에서 인용한 추정값이다. 정확한
  계약상의 지원기간은 별도 검증 필요.
* support_status는 오늘 날짜 기준으로 자동 도출 (END/LIMITED/SUPPORTED).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Code
from masters.models import Component, ComponentAlias, ConfigurationComponentMapping


TODAY = date(2026, 5, 10)


@dataclass
class Entry:
    type_code: str  # language|framework|library|runtime|middleware|OS|DB|기타
    product_name: str
    version: str
    vendor_name: str = ""
    cpe_name: str = ""
    eos_date: Optional[date] = None
    eol_date: Optional[date] = None


def _cpe(vendor: str, product: str, version: str) -> str:
    """간이 CPE 2.3 (application) 빌더. 실제 NVD 항목과 표기가 일치할 때만 사용."""
    return f"cpe:2.3:a:{vendor}:{product}:{version}:*:*:*:*:*:*:*"


def _cpe_o(vendor: str, product: str, version: str) -> str:
    return f"cpe:2.3:o:{vendor}:{product}:{version}:*:*:*:*:*:*:*"


# === 데이터 정의 ===
# 각 항목: Entry(type, product, version, vendor, cpe, eos, eol)

ENTRIES: list[Entry] = []

# ---------- LANGUAGE ----------
# C# (Microsoft)
ENTRIES += [
    Entry("language", "C#", "9.0", "Microsoft", "", date(2022, 11, 8), date(2022, 11, 8)),
    Entry("language", "C#", "10.0", "Microsoft", "", date(2024, 5, 14), date(2024, 5, 14)),
    Entry("language", "C#", "11.0", "Microsoft", "", date(2024, 11, 12), date(2025, 5, 13)),
    Entry("language", "C#", "12.0", "Microsoft", "", date(2026, 11, 10), date(2026, 11, 10)),
]

# JavaScript (ECMA, 언어 자체엔 CPE 없음)
ENTRIES += [
    Entry("language", "JavaScript", "ES2022", "ECMA International", "", None, None),
    Entry("language", "JavaScript", "ES2023", "ECMA International", "", None, None),
    Entry("language", "JavaScript", "ES2024", "ECMA International", "", None, None),
]

# JSP (Jakarta Server Pages, 구 JavaServer Pages)
ENTRIES += [
    Entry("language", "JSP", "2.3", "Oracle", "", date(2017, 9, 30), date(2017, 9, 30)),
    Entry("language", "JSP", "3.0", "Eclipse Foundation", "", None, None),
    Entry("language", "JSP", "3.1", "Eclipse Foundation", "", None, None),
]

# TypeScript (Microsoft)
ENTRIES += [
    Entry("language", "TypeScript", "4.9", "Microsoft", _cpe("microsoft", "typescript", "4.9"), date(2023, 5, 15), date(2024, 5, 15)),
    Entry("language", "TypeScript", "5.0", "Microsoft", _cpe("microsoft", "typescript", "5.0"), date(2023, 11, 14), date(2024, 11, 14)),
    Entry("language", "TypeScript", "5.4", "Microsoft", _cpe("microsoft", "typescript", "5.4"), date(2024, 9, 9), date(2025, 9, 9)),
    Entry("language", "TypeScript", "5.7", "Microsoft", _cpe("microsoft", "typescript", "5.7"), date(2026, 5, 22), date(2027, 5, 22)),
]

# HTML (W3C / WHATWG, Living Standard, CPE 없음)
ENTRIES += [
    Entry("language", "HTML", "5", "WHATWG", "", None, None),
]

# Kotlin (JetBrains)
ENTRIES += [
    Entry("language", "Kotlin", "1.9.25", "JetBrains", _cpe("jetbrains", "kotlin", "1.9.25"), None, None),
    Entry("language", "Kotlin", "2.0.21", "JetBrains", _cpe("jetbrains", "kotlin", "2.0.21"), None, None),
    Entry("language", "Kotlin", "2.1.0", "JetBrains", _cpe("jetbrains", "kotlin", "2.1.0"), None, None),
]

# Swift (Apple)
ENTRIES += [
    Entry("language", "Swift", "5.9", "Apple", _cpe("apple", "swift", "5.9"), None, None),
    Entry("language", "Swift", "5.10", "Apple", _cpe("apple", "swift", "5.10"), None, None),
    Entry("language", "Swift", "6.0", "Apple", _cpe("apple", "swift", "6.0"), None, None),
]

# VB.NET (Microsoft, language; CPE는 NVD 미수록)
ENTRIES += [
    Entry("language", "VB.NET", "16.0", "Microsoft", "", date(2024, 5, 14), date(2024, 5, 14)),
    Entry("language", "VB.NET", "17.0", "Microsoft", "", None, None),
]

# XML (W3C, 사양; CPE 없음)
ENTRIES += [
    Entry("language", "XML", "1.0", "W3C", "", None, None),
    Entry("language", "XML", "1.1", "W3C", "", None, None),
]

# Visual Basic (legacy VB6)
ENTRIES += [
    Entry("language", "Visual Basic", "6.0", "Microsoft", "", date(2008, 4, 8), date(2008, 4, 8)),
]

# Java (language spec, Oracle JDK 기준)
ENTRIES += [
    Entry("language", "Java", "8", "Oracle", _cpe("oracle", "jdk", "1.8.0"), date(2022, 3, 31), date(2030, 12, 31)),
    Entry("language", "Java", "11", "Oracle", _cpe("oracle", "jdk", "11"), date(2023, 9, 30), date(2026, 9, 30)),
    Entry("language", "Java", "17", "Oracle", _cpe("oracle", "jdk", "17"), date(2026, 9, 30), date(2029, 9, 30)),
    Entry("language", "Java", "21", "Oracle", _cpe("oracle", "jdk", "21"), date(2028, 9, 30), date(2031, 9, 30)),
]

# ABAP (SAP NetWeaver 기반, 언어 직접 CPE 없음)
ENTRIES += [
    Entry("language", "ABAP", "7.50", "SAP", "", None, None),
    Entry("language", "ABAP", "7.55", "SAP", "", None, None),
    Entry("language", "ABAP", "7.58", "SAP", "", None, None),
]

# LotusScript (HCL/IBM Notes 내장 언어)
ENTRIES += [
    Entry("language", "LotusScript", "11", "HCL", "", date(2024, 6, 1), date(2024, 6, 1)),
    Entry("language", "LotusScript", "12", "HCL", "", None, None),
    Entry("language", "LotusScript", "14", "HCL", "", None, None),
]

# Formula (Lotus/Notes Formula Language)
ENTRIES += [
    Entry("language", "Formula", "11", "HCL", "", date(2024, 6, 1), date(2024, 6, 1)),
    Entry("language", "Formula", "12", "HCL", "", None, None),
    Entry("language", "Formula", "14", "HCL", "", None, None),
]

# C++ (ISO 표준, CPE 없음)
ENTRIES += [
    Entry("language", "C++", "C++17", "ISO", "", None, None),
    Entry("language", "C++", "C++20", "ISO", "", None, None),
    Entry("language", "C++", "C++23", "ISO", "", None, None),
]

# ---------- FRAMEWORK ----------
# .NET Framework (legacy 4.x; C#/VB.NET 페어링)
ENTRIES += [
    Entry("framework", ".NET Framework", "4.6.2", "Microsoft", _cpe("microsoft", ".net_framework", "4.6.2"), date(2027, 1, 12), date(2027, 1, 12)),
    Entry("framework", ".NET Framework", "4.7.2", "Microsoft", _cpe("microsoft", ".net_framework", "4.7.2"), None, None),
    Entry("framework", ".NET Framework", "4.8", "Microsoft", _cpe("microsoft", ".net_framework", "4.8"), None, None),
    Entry("framework", ".NET Framework", "4.8.1", "Microsoft", _cpe("microsoft", ".net_framework", "4.8.1"), None, None),
]

# Angular (Google)
ENTRIES += [
    Entry("framework", "Angular", "16.2", "Google", _cpe("angular", "angular", "16.2"), date(2024, 11, 8), date(2024, 11, 8)),
    Entry("framework", "Angular", "17.3", "Google", _cpe("angular", "angular", "17.3"), date(2025, 5, 8), date(2025, 5, 8)),
    Entry("framework", "Angular", "18.2", "Google", _cpe("angular", "angular", "18.2"), date(2025, 11, 21), date(2025, 11, 21)),
    Entry("framework", "Angular", "19.0", "Google", _cpe("angular", "angular", "19.0"), date(2026, 5, 19), date(2026, 5, 19)),
]

# Vue.js
ENTRIES += [
    Entry("framework", "Vue.js", "2.7.16", "Vue.js", _cpe("vuejs", "vue.js", "2.7.16"), date(2023, 12, 31), date(2023, 12, 31)),
    Entry("framework", "Vue.js", "3.4", "Vue.js", _cpe("vuejs", "vue.js", "3.4"), None, None),
    Entry("framework", "Vue.js", "3.5", "Vue.js", _cpe("vuejs", "vue.js", "3.5"), None, None),
]

# MyBatis
ENTRIES += [
    Entry("framework", "MyBatis", "3.5.13", "MyBatis", _cpe("mybatis", "mybatis", "3.5.13"), None, None),
    Entry("framework", "MyBatis", "3.5.16", "MyBatis", _cpe("mybatis", "mybatis", "3.5.16"), None, None),
]

# ---------- LIBRARY ----------
# jQuery (OpenJS Foundation)
ENTRIES += [
    Entry("library", "jQuery", "3.6.4", "OpenJS Foundation", _cpe("jquery", "jquery", "3.6.4"), None, None),
    Entry("library", "jQuery", "3.7.1", "OpenJS Foundation", _cpe("jquery", "jquery", "3.7.1"), None, None),
    Entry("library", "jQuery", "4.0.0", "OpenJS Foundation", _cpe("jquery", "jquery", "4.0.0"), None, None),
]

# Ext JS (Sencha)
ENTRIES += [
    Entry("library", "Ext JS", "6.7.0", "Sencha", _cpe("sencha", "ext_js", "6.7.0"), None, None),
    Entry("library", "Ext JS", "7.7.0", "Sencha", _cpe("sencha", "ext_js", "7.7.0"), None, None),
    Entry("library", "Ext JS", "7.8.0", "Sencha", _cpe("sencha", "ext_js", "7.8.0"), None, None),
]

# Bootstrap (getbootstrap)
ENTRIES += [
    Entry("library", "Bootstrap", "4.6.2", "Bootstrap", _cpe("getbootstrap", "bootstrap", "4.6.2"), None, None),
    Entry("library", "Bootstrap", "5.0.2", "Bootstrap", _cpe("getbootstrap", "bootstrap", "5.0.2"), None, None),
    Entry("library", "Bootstrap", "5.3.3", "Bootstrap", _cpe("getbootstrap", "bootstrap", "5.3.3"), None, None),
]

# Dojo Toolkit
ENTRIES += [
    Entry("library", "Dojo", "1.17.3", "Dojo Foundation", _cpe("dojotoolkit", "dojo", "1.17.3"), None, None),
    Entry("library", "Dojo", "1.18.0", "Dojo Foundation", _cpe("dojotoolkit", "dojo", "1.18.0"), None, None),
]

# React (Meta)
ENTRIES += [
    Entry("library", "React", "17.0.2", "Meta", _cpe("facebook", "react", "17.0.2"), None, None),
    Entry("library", "React", "18.3.1", "Meta", _cpe("facebook", "react", "18.3.1"), None, None),
    Entry("library", "React", "19.0.0", "Meta", _cpe("facebook", "react", "19.0.0"), None, None),
]

# MFC (Microsoft Foundation Class) — Visual C++ Redistributable에서 추적됨
ENTRIES += [
    Entry("library", "MFC", "14.29 (VS2019)", "Microsoft", "", None, None),
    Entry("library", "MFC", "14.36 (VS2022)", "Microsoft", "", None, None),
]

# ---------- RUNTIME ----------
# OpenJDK (java alias 페어링과 통합)
ENTRIES += [
    Entry("runtime", "OpenJDK", "11", "Eclipse Adoptium", _cpe("openjdk", "openjdk", "11"), date(2024, 10, 31), date(2027, 10, 31)),
    Entry("runtime", "OpenJDK", "17", "Eclipse Adoptium", _cpe("openjdk", "openjdk", "17"), date(2027, 10, 31), date(2029, 10, 31)),
    Entry("runtime", "OpenJDK", "21", "Eclipse Adoptium", _cpe("openjdk", "openjdk", "21"), date(2028, 10, 31), date(2030, 10, 31)),
]

# .NET (구 .NET Core; alias ".Net core" + C#/VB.NET 페어링과 통합)
ENTRIES += [
    Entry("runtime", ".NET", "6.0", "Microsoft", _cpe("microsoft", ".net", "6.0"), date(2024, 11, 12), date(2024, 11, 12)),
    Entry("runtime", ".NET", "8.0", "Microsoft", _cpe("microsoft", ".net", "8.0"), date(2026, 11, 10), date(2026, 11, 10)),
    Entry("runtime", ".NET", "9.0", "Microsoft", _cpe("microsoft", ".net", "9.0"), date(2026, 5, 12), date(2026, 5, 12)),
]

# Node.js
ENTRIES += [
    Entry("runtime", "Node.js", "18", "OpenJS Foundation", _cpe("nodejs", "node.js", "18"), date(2025, 4, 30), date(2025, 4, 30)),
    Entry("runtime", "Node.js", "20", "OpenJS Foundation", _cpe("nodejs", "node.js", "20"), date(2026, 4, 30), date(2026, 4, 30)),
    Entry("runtime", "Node.js", "22", "OpenJS Foundation", _cpe("nodejs", "node.js", "22"), date(2027, 4, 30), date(2027, 4, 30)),
    Entry("runtime", "Node.js", "24", "OpenJS Foundation", _cpe("nodejs", "node.js", "24"), date(2028, 4, 30), date(2028, 4, 30)),
]

# ---------- MIDDLEWARE ----------
# Lotus Domino (HCL Domino server)
ENTRIES += [
    Entry("middleware", "HCL Domino", "11.0", "HCL", _cpe("hcltechsw", "hcl_domino", "11.0"), date(2024, 6, 1), date(2024, 6, 1)),
    Entry("middleware", "HCL Domino", "12.0", "HCL", _cpe("hcltechsw", "hcl_domino", "12.0"), None, None),
    Entry("middleware", "HCL Domino", "14.0", "HCL", _cpe("hcltechsw", "hcl_domino", "14.0"), None, None),
]

# Lotus Notes (HCL Notes client; alias "NOTES")
ENTRIES += [
    Entry("middleware", "HCL Notes", "11.0", "HCL", _cpe("hcltechsw", "hcl_notes", "11.0"), date(2024, 6, 1), date(2024, 6, 1)),
    Entry("middleware", "HCL Notes", "12.0", "HCL", _cpe("hcltechsw", "hcl_notes", "12.0"), None, None),
    Entry("middleware", "HCL Notes", "14.0", "HCL", _cpe("hcltechsw", "hcl_notes", "14.0"), None, None),
]

# ---------- OS ----------
# Windows Server (Microsoft)
ENTRIES += [
    Entry("OS", "Windows Server", "2016", "Microsoft", _cpe_o("microsoft", "windows_server_2016", "-"), date(2022, 1, 11), date(2027, 1, 12)),
    Entry("OS", "Windows Server", "2019", "Microsoft", _cpe_o("microsoft", "windows_server_2019", "-"), date(2024, 1, 9), date(2029, 1, 9)),
    Entry("OS", "Windows Server", "2022", "Microsoft", _cpe_o("microsoft", "windows_server_2022", "-"), date(2026, 10, 13), date(2031, 10, 14)),
    Entry("OS", "Windows Server", "2025", "Microsoft", _cpe_o("microsoft", "windows_server_2025", "-"), date(2029, 10, 9), date(2034, 10, 10)),
]

# Amazon Linux
ENTRIES += [
    Entry("OS", "Amazon Linux", "2", "Amazon", _cpe_o("amazon", "amazon_linux", "2"), date(2026, 6, 30), date(2026, 6, 30)),
    Entry("OS", "Amazon Linux", "2023", "Amazon", _cpe_o("amazon", "amazon_linux", "2023"), date(2028, 3, 15), date(2028, 3, 15)),
]

# Ubuntu (Canonical)
ENTRIES += [
    Entry("OS", "Ubuntu", "20.04", "Canonical", _cpe_o("canonical", "ubuntu_linux", "20.04"), date(2025, 4, 30), date(2030, 4, 30)),
    Entry("OS", "Ubuntu", "22.04", "Canonical", _cpe_o("canonical", "ubuntu_linux", "22.04"), date(2027, 4, 30), date(2032, 4, 30)),
    Entry("OS", "Ubuntu", "24.04", "Canonical", _cpe_o("canonical", "ubuntu_linux", "24.04"), date(2029, 4, 30), date(2034, 4, 30)),
]

# Red Hat Enterprise Linux
ENTRIES += [
    Entry("OS", "Red Hat Enterprise Linux", "7", "Red Hat", _cpe_o("redhat", "enterprise_linux", "7"), date(2024, 6, 30), date(2028, 6, 30)),
    Entry("OS", "Red Hat Enterprise Linux", "8", "Red Hat", _cpe_o("redhat", "enterprise_linux", "8"), date(2029, 5, 31), date(2032, 5, 31)),
    Entry("OS", "Red Hat Enterprise Linux", "9", "Red Hat", _cpe_o("redhat", "enterprise_linux", "9"), date(2032, 5, 31), date(2035, 5, 31)),
]

# ---------- DB ----------
# Microsoft SQL Server
ENTRIES += [
    Entry("DB", "Microsoft SQL Server", "2017", "Microsoft", _cpe("microsoft", "sql_server", "2017"), date(2022, 10, 11), date(2027, 10, 12)),
    Entry("DB", "Microsoft SQL Server", "2019", "Microsoft", _cpe("microsoft", "sql_server", "2019"), date(2025, 1, 7), date(2030, 1, 8)),
    Entry("DB", "Microsoft SQL Server", "2022", "Microsoft", _cpe("microsoft", "sql_server", "2022"), date(2028, 1, 11), date(2033, 1, 11)),
]

# Oracle Database (alias "Oracle"는 DB로 해석)
ENTRIES += [
    Entry("DB", "Oracle Database", "19c", "Oracle", _cpe("oracle", "database_server", "19c"), date(2027, 4, 30), date(2030, 4, 30)),
    Entry("DB", "Oracle Database", "21c", "Oracle", _cpe("oracle", "database_server", "21c"), date(2024, 4, 30), date(2027, 4, 30)),
    Entry("DB", "Oracle Database", "23ai", "Oracle", _cpe("oracle", "database_server", "23ai"), None, None),
]

# SAP MaxDB (alias "MAX DB")
ENTRIES += [
    Entry("DB", "SAP MaxDB", "7.9", "SAP", _cpe("sap", "maxdb", "7.9"), None, None),
]

# MongoDB
ENTRIES += [
    Entry("DB", "MongoDB", "6.0", "MongoDB Inc.", _cpe("mongodb", "mongodb", "6.0"), date(2025, 7, 31), date(2025, 7, 31)),
    Entry("DB", "MongoDB", "7.0", "MongoDB Inc.", _cpe("mongodb", "mongodb", "7.0"), date(2026, 8, 31), date(2026, 8, 31)),
    Entry("DB", "MongoDB", "8.0", "MongoDB Inc.", _cpe("mongodb", "mongodb", "8.0"), date(2027, 10, 31), date(2027, 10, 31)),
]

# MariaDB
ENTRIES += [
    Entry("DB", "MariaDB", "10.6", "MariaDB Foundation", _cpe("mariadb", "mariadb", "10.6"), date(2026, 7, 31), date(2026, 7, 31)),
    Entry("DB", "MariaDB", "10.11", "MariaDB Foundation", _cpe("mariadb", "mariadb", "10.11"), date(2028, 2, 28), date(2028, 2, 28)),
    Entry("DB", "MariaDB", "11.4", "MariaDB Foundation", _cpe("mariadb", "mariadb", "11.4"), date(2029, 5, 31), date(2029, 5, 31)),
]

# PostgreSQL
ENTRIES += [
    Entry("DB", "PostgreSQL", "14", "PostgreSQL Global Development Group", _cpe("postgresql", "postgresql", "14"), date(2026, 11, 12), date(2026, 11, 12)),
    Entry("DB", "PostgreSQL", "15", "PostgreSQL Global Development Group", _cpe("postgresql", "postgresql", "15"), date(2027, 11, 11), date(2027, 11, 11)),
    Entry("DB", "PostgreSQL", "16", "PostgreSQL Global Development Group", _cpe("postgresql", "postgresql", "16"), date(2028, 11, 9), date(2028, 11, 9)),
    Entry("DB", "PostgreSQL", "17", "PostgreSQL Global Development Group", _cpe("postgresql", "postgresql", "17"), date(2029, 11, 8), date(2029, 11, 8)),
]

# ---------- 기타 ----------
ENTRIES += [
    Entry("기타", "기타", "-", "", "", None, None),
]


# === Alias 사전 ===
# 검색어 → product_name 매칭. 케이스 무관 비교는 조회시점에서 수행.
# 한 alias가 여러 product에 매핑될 수 있다(예: "java" → Java + OpenJDK).
ALIASES: dict[str, list[str]] = {
    # language
    "C#": ["csharp", "cs", "c sharp"],
    "JavaScript": ["js", "ecmascript", "javascript"],
    "JSP": ["jakarta server pages", "javaserver pages"],
    "TypeScript": ["ts", "typescript"],
    "HTML": ["html5", "hypertext markup language"],
    "Kotlin": ["kt", "kotlin"],
    "Swift": ["swift"],
    "VB.NET": ["vbnet", "vb.net", "visual basic .net"],
    "XML": ["xml"],
    "Visual Basic": ["vb", "vb6", "visual basic"],
    "Java": ["java", "jdk"],
    "ABAP": ["sap abap", "abap"],
    "LotusScript": ["notes script", "lotusscript"],
    "Formula": ["lotus formula", "formula language"],
    "C++": ["cpp", "c plus plus"],
    # framework
    ".NET Framework": ["dotnet framework", ".net framework", "netfx"],
    "Angular": ["ng", "angular2", "angular.io"],
    "Vue.js": ["vue", "vuejs"],
    "MyBatis": ["ibatis", "mybatis spring"],
    # library
    "jQuery": ["jq", "jquery"],
    "Ext JS": ["extjs", "sencha", "sencha extjs"],
    "Bootstrap": ["bootstrap", "twitter bootstrap"],
    "Dojo": ["dojo toolkit", "dojo"],
    "React": ["react.js", "reactjs"],
    "MFC": ["microsoft foundation class", "mfc"],
    # runtime
    "OpenJDK": ["java", "jdk", "openjdk", "adoptium", "temurin"],
    ".NET": ["dotnet", ".net core", "dotnet core", "net core"],
    "Node.js": ["nodejs", "node", "node js"],
    # middleware
    "HCL Domino": ["lotus domino", "ibm domino", "domino"],
    "HCL Notes": ["lotus notes", "ibm notes", "notes"],
    # OS
    "Windows Server": ["windows", "win server", "winsrv", "win"],
    "Amazon Linux": ["amzn", "aws linux", "amazonlinux"],
    "Ubuntu": ["canonical", "ubuntu linux"],
    "Red Hat Enterprise Linux": ["rhel", "redhat", "redhat linux", "red hat"],
    # DB
    "Microsoft SQL Server": ["mssql", "sql server", "ms sql"],
    "Oracle Database": ["oracle", "oracle db", "oracledb"],
    "SAP MaxDB": ["maxdb", "max db", "sapdb"],
    "MongoDB": ["mongo"],
    "MariaDB": ["maria"],
    "PostgreSQL": ["postgres", "postgre", "pg"],
    # 기타
    "기타": ["etc", "기타", "other"],
}


def derive_support_status_code(eos: Optional[date], eol: Optional[date]) -> str:
    if eol and eol < TODAY:
        return "END"
    if eos and eos < TODAY:
        return "LIMITED"
    return "SUPPORTED"


class Command(BaseCommand):
    help = (
        "컴포넌트 마스터 전체 삭제 후 표준 컴포넌트(LTS/안정판 위주, "
        "CVE 분석을 위한 CPE 2.3 표기 포함)로 재시드한다."
    )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        type_codes = {
            tc: Code.objects.filter(group__key="component_type", code=tc, is_active=True).first()
            for tc in {"language", "framework", "library", "runtime", "middleware", "OS", "DB", "기타"}
        }
        missing_types = [k for k, v in type_codes.items() if v is None]
        if missing_types:
            self.stderr.write(self.style.ERROR(
                f"component_type 코드 누락: {missing_types}. seed_codes 먼저 실행 필요."
            ))
            return

        support_codes = {
            sc: Code.objects.filter(group__key="support_status", code=sc, is_active=True).first()
            for sc in ("SUPPORTED", "LIMITED", "END")
        }
        missing_supports = [k for k, v in support_codes.items() if v is None]
        if missing_supports:
            self.stderr.write(self.style.ERROR(
                f"support_status 코드 누락: {missing_supports}. seed_codes 먼저 실행 필요."
            ))
            return

        deleted_mappings = ConfigurationComponentMapping.objects.count()
        ConfigurationComponentMapping.objects.all().delete()
        deleted = Component.objects.count()
        Component.objects.all().delete()
        deleted_aliases = ComponentAlias.objects.count()
        ComponentAlias.objects.all().delete()
        self.stdout.write(
            f"기존 Component {deleted}건, ConfigurationComponentMapping {deleted_mappings}건, "
            f"ComponentAlias {deleted_aliases}건 삭제"
        )

        per_type_counts: dict[str, int] = {}
        for e in ENTRIES:
            tc = type_codes[e.type_code]
            sc_key = derive_support_status_code(e.eos_date, e.eol_date)
            sc = support_codes[sc_key]
            Component.objects.create(
                product_name=e.product_name,
                version=e.version,
                vendor_name=e.vendor_name,
                cpe_name=e.cpe_name,
                eos_date=e.eos_date,
                eol_date=e.eol_date,
                component_type_code=tc,
                support_status_code=sc,
                created_by="seed",
                updated_by="seed",
            )
            per_type_counts[e.type_code] = per_type_counts.get(e.type_code, 0) + 1

        alias_count = 0
        for product_name, alias_list in ALIASES.items():
            seen = set()
            for raw in alias_list:
                a = (raw or "").strip()
                if not a or a in seen:
                    continue
                seen.add(a)
                ComponentAlias.objects.create(product_name=product_name, alias=a)
                alias_count += 1

        self.stdout.write(self.style.SUCCESS(f"총 {len(ENTRIES)}건 시드 완료"))
        for k in ("language", "framework", "library", "runtime", "middleware", "OS", "DB", "기타"):
            self.stdout.write(f"  {k:<12s} : {per_type_counts.get(k, 0)}건")
        self.stdout.write(self.style.SUCCESS(f"Alias {alias_count}건 시드 완료"))
