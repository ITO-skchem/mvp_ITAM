from django.core.management.base import BaseCommand

from core.models import Code, CodeGroup


def _inv(code, product, version, cpe_vendor=None, cpe_product=None, cpe_version=None):
    """컴포넌트 제품·버전 코드 한 건. name = '제품명' + 공백 + '버전'. extra는 CVE/CPE·자동매핑 확장용."""
    name = f"{product} {version}"
    extra = {
        "inventory": {
            "product_label": product,
            "version_label": version,
        }
    }
    if cpe_vendor and cpe_product:
        extra["inventory"]["cpe_hint"] = {
            "part": "a",
            "vendor": cpe_vendor,
            "product": cpe_product,
            "version": cpe_version if cpe_version is not None else version,
        }
    return (code, name, extra)


# 그룹별 상위 3개 제품(엔터프라이즈 관례)의 메이저·대표 라인이 빠지지 않도록 구성.
# code 값은 그룹 간 유일(컴포넌트 마스터에서 code 기준 중복 제거)하도록 접두·이름을 분리.
PRODUCT_VERSION_GROUPS = {
    "language": {
        "name": "Language",
        "description": "프로그래밍 언어 및 언어 레벨 버전. 표시: '제품명 버전'. CVE/CPE 매핑은 extra.inventory.cpe_hint 확장.",
        "codes": [
            # Java
            _inv("lang_java_8", "Java", "8", "oracle", "jdk", "8"),
            _inv("lang_java_11", "Java", "11", "oracle", "jdk", "11"),
            _inv("lang_java_17", "Java", "17", "oracle", "jdk", "17"),
            _inv("lang_java_21", "Java", "21", "oracle", "jdk", "21"),
            # Python
            _inv("lang_python_3_9", "Python", "3.9", "python", "python", "3.9"),
            _inv("lang_python_3_10", "Python", "3.10", "python", "python", "3.10"),
            _inv("lang_python_3_11", "Python", "3.11", "python", "python", "3.11"),
            _inv("lang_python_3_12", "Python", "3.12", "python", "python", "3.12"),
            _inv("lang_python_3_13", "Python", "3.13", "python", "python", "3.13"),
            # Node.js — 런타임 그룹과 코드명 중복 방지(컴포넌트명은 Code.name으로 관리)
            _inv("lang_nodejs_18", "Node.js (언어)", "18", "nodejs", "node.js", "18"),
            _inv("lang_nodejs_20", "Node.js (언어)", "20", "nodejs", "node.js", "20"),
            _inv("lang_nodejs_22", "Node.js (언어)", "22", "nodejs", "node.js", "22"),
            # 기타 주요 언어
            _inv("lang_typescript_5", "TypeScript", "5", "microsoft", "typescript", "5"),
            _inv("lang_go_1_21", "Go", "1.21", "golang", "go", "1.21"),
            _inv("lang_go_1_22", "Go", "1.22", "golang", "go", "1.22"),
            _inv("lang_go_1_23", "Go", "1.23", "golang", "go", "1.23"),
            _inv("lang_csharp_12", "C#", "12", "microsoft", "c#", "12"),
            _inv("lang_kotlin_1_9", "Kotlin", "1.9", "jetbrains", "kotlin", "1.9"),
            _inv("lang_kotlin_2_0", "Kotlin", "2.0", "jetbrains", "kotlin", "2.0"),
            _inv("lang_php_8_2", "PHP", "8.2", "php", "php", "8.2"),
            _inv("lang_php_8_3", "PHP", "8.3", "php", "php", "8.3"),
            _inv("lang_ruby_3_2", "Ruby", "3.2", "ruby-lang", "ruby", "3.2"),
            _inv("lang_ruby_3_3", "Ruby", "3.3", "ruby-lang", "ruby", "3.3"),
            _inv("lang_rust_1_76", "Rust", "1.76", "rust-lang", "rust", "1.76"),
            _inv("lang_rust_1_80", "Rust", "1.80", "rust-lang", "rust", "1.80"),
            _inv("lang_swift_5_9", "Swift", "5.9", "apple", "swift", "5.9"),
            _inv("lang_swift_5_10", "Swift", "5.10", "apple", "swift", "5.10"),
            _inv("lang_scala_3", "Scala", "3", "apache", "scala", "3"),
            _inv("lang_dart_3", "Dart", "3", "google", "dart", "3"),
        ],
    },
    "runtime": {
        "name": "Runtime",
        "description": "실행 환경(JVM, Node, .NET 등). language와 동일 스택이어도 code는 rt_ 접두로 구분.",
        "codes": [
            # JVM / OpenJDK 배포판
            _inv("rt_temurin_8", "Eclipse Temurin", "8", "eclipse", "openjdk", "8"),
            _inv("rt_temurin_11", "Eclipse Temurin", "11", "eclipse", "openjdk", "11"),
            _inv("rt_temurin_17", "Eclipse Temurin", "17", "eclipse", "openjdk", "17"),
            _inv("rt_temurin_21", "Eclipse Temurin", "21", "eclipse", "openjdk", "21"),
            _inv("rt_corretto_11", "Amazon Corretto", "11", "amazon", "corretto", "11"),
            _inv("rt_corretto_17", "Amazon Corretto", "17", "amazon", "corretto", "17"),
            _inv("rt_corretto_21", "Amazon Corretto", "21", "amazon", "corretto", "21"),
            _inv("rt_graalvm_17", "GraalVM", "17", "oracle", "graalvm", "17"),
            _inv("rt_graalvm_21", "GraalVM", "21", "oracle", "graalvm", "21"),
            # Node 계열
            _inv("rt_nodejs_18", "Node.js (런타임)", "18", "nodejs", "node.js", "18"),
            _inv("rt_nodejs_20", "Node.js (런타임)", "20", "nodejs", "node.js", "20"),
            _inv("rt_nodejs_22", "Node.js (런타임)", "22", "nodejs", "node.js", "22"),
            _inv("rt_deno_1", "Deno", "1", "denoland", "deno", "1"),
            _inv("rt_deno_2", "Deno", "2", "denoland", "deno", "2"),
            _inv("rt_bun_1", "Bun", "1", "oven-sh", "bun", "1"),
            # .NET
            _inv("rt_dotnet_6", ".NET", "6", "microsoft", ".net", "6"),
            _inv("rt_dotnet_8", ".NET", "8", "microsoft", ".net", "8"),
            _inv("rt_dotnet_9", ".NET", "9", "microsoft", ".net", "9"),
            # CPython 인터프리터(런타임 관점)
            _inv("rt_cpython_3_11", "CPython", "3.11", "python", "python", "3.11"),
            _inv("rt_cpython_3_12", "CPython", "3.12", "python", "python", "3.12"),
            _inv("rt_cpython_3_13", "CPython", "3.13", "python", "python", "3.13"),
            _inv("rt_wasmtime_20", "Wasmtime", "20", "bytecodealliance", "wasmtime", "20"),
        ],
    },
    "framework": {
        "name": "Framework",
        "description": "애플리케이션 프레임워크. 상위: Spring Boot, Django, React 메이저 라인 정비.",
        "codes": [
            _inv("fw_spring_boot_2", "Spring Boot", "2", "vmware", "spring_boot", "2"),
            _inv("fw_spring_boot_3", "Spring Boot", "3", "vmware", "spring_boot", "3"),
            _inv("fw_spring_boot_3_4", "Spring Boot", "3.4", "vmware", "spring_boot", "3.4"),
            _inv("fw_spring_framework_5", "Spring Framework", "5", "vmware", "spring_framework", "5"),
            _inv("fw_spring_framework_6", "Spring Framework", "6", "vmware", "spring_framework", "6"),
            _inv("fw_django_4", "Django", "4", "djangoproject", "django", "4"),
            _inv("fw_django_5", "Django", "5", "djangoproject", "django", "5"),
            _inv("fw_django_5_2", "Django", "5.2", "djangoproject", "django", "5.2"),
            _inv("fw_react_17", "React", "17", "facebook", "react", "17"),
            _inv("fw_react_18", "React", "18", "facebook", "react", "18"),
            _inv("fw_react_19", "React", "19", "facebook", "react", "19"),
            _inv("fw_vue_3", "Vue", "3", "vuejs", "vue.js", "3"),
            _inv("fw_angular_17", "Angular", "17", "google", "angular", "17"),
            _inv("fw_angular_18", "Angular", "18", "google", "angular", "18"),
            _inv("fw_angular_19", "Angular", "19", "google", "angular", "19"),
            _inv("fw_express_4", "Express", "4", "expressjs", "express", "4"),
            _inv("fw_nestjs_10", "NestJS", "10", "nestjs", "nestjs", "10"),
            _inv("fw_nestjs_11", "NestJS", "11", "nestjs", "nestjs", "11"),
            _inv("fw_nextjs_14", "Next.js", "14", "vercel", "next.js", "14"),
            _inv("fw_nextjs_15", "Next.js", "15", "vercel", "next.js", "15"),
            _inv("fw_aspnet_core_8", "ASP.NET Core", "8", "microsoft", "asp.net_core", "8"),
            _inv("fw_aspnet_core_9", "ASP.NET Core", "9", "microsoft", "asp.net_core", "9"),
            _inv("fw_rails_7", "Ruby on Rails", "7", "rubyonrails", "rails", "7"),
            _inv("fw_rails_8", "Ruby on Rails", "8", "rubyonrails", "rails", "8"),
            _inv("fw_laravel_10", "Laravel", "10", "laravel", "laravel", "10"),
            _inv("fw_laravel_11", "Laravel", "11", "laravel", "laravel", "11"),
            _inv("fw_flask_3", "Flask", "3", "palletsprojects", "flask", "3"),
            _inv("fw_fastapi_0_115", "FastAPI", "0.115", "tiangolo", "fastapi", "0.115"),
            _inv("fw_quarkus_3", "Quarkus", "3", "redhat", "quarkus", "3"),
        ],
    },
    "library": {
        "name": "Library",
        "description": "주요 라이브러리. 상위: Jackson, Hibernate ORM, Netty.",
        "codes": [
            _inv("lib_jackson_2_14", "Jackson", "2.14", "fasterxml", "jackson-databind", "2.14"),
            _inv("lib_jackson_2_17", "Jackson", "2.17", "fasterxml", "jackson-databind", "2.17"),
            _inv("lib_jackson_2_18", "Jackson", "2.18", "fasterxml", "jackson-databind", "2.18"),
            _inv("lib_hibernate_5", "Hibernate ORM", "5", "hibernate", "hibernate_orm", "5"),
            _inv("lib_hibernate_6", "Hibernate ORM", "6", "hibernate", "hibernate_orm", "6"),
            _inv("lib_hibernate_6_4", "Hibernate ORM", "6.4", "hibernate", "hibernate_orm", "6.4"),
            _inv("lib_netty_4_1", "Netty", "4.1", "netty", "netty", "4.1"),
            _inv("lib_netty_4_2", "Netty", "4.2", "netty", "netty", "4.2"),
            _inv("lib_gson_2", "Gson", "2", "google", "gson", "2"),
            _inv("lib_okhttp_4", "OkHttp", "4", "squareup", "okhttp", "4"),
            _inv("lib_mybatis_3", "MyBatis", "3", "mybatis", "mybatis", "3"),
            _inv("lib_springdoc_2", "springdoc-openapi", "2", "springdoc", "springdoc-openapi", "2"),
            _inv("lib_slf4j_2", "SLF4J", "2", "qos-ch", "slf4j", "2"),
            _inv("lib_log4j_2", "Apache Log4j", "2", "apache", "log4j", "2"),
            _inv("lib_junit_5", "JUnit", "5", "junit", "junit5", "5"),
            _inv("lib_mockito_5", "Mockito", "5", "mockito", "mockito", "5"),
            _inv("lib_commons_lang_3", "Apache Commons Lang", "3", "apache", "commons-lang3", "3"),
            _inv("lib_axios_1", "Axios", "1", "axios", "axios", "1"),
            _inv("lib_lodash_4", "Lodash", "4", "lodash", "lodash", "4"),
            _inv("lib_jquery_3", "jQuery", "3", "jquery", "jquery", "3"),
            _inv("lib_bootstrap_5", "Bootstrap", "5", "getbootstrap", "bootstrap", "5"),
        ],
    },
    "middleware": {
        "name": "Middleware",
        "description": "WAS·웹서버·메시징 등. 상위: Tomcat, Nginx, Kafka.",
        "codes": [
            _inv("mw_tomcat_8", "Apache Tomcat", "8.5", "apache", "tomcat", "8.5"),
            _inv("mw_tomcat_9", "Apache Tomcat", "9", "apache", "tomcat", "9"),
            _inv("mw_tomcat_10", "Apache Tomcat", "10", "apache", "tomcat", "10"),
            _inv("mw_tomcat_11", "Apache Tomcat", "11", "apache", "tomcat", "11"),
            _inv("mw_nginx_1_22", "Nginx", "1.22", "nginx", "nginx", "1.22"),
            _inv("mw_nginx_1_24", "Nginx", "1.24", "nginx", "nginx", "1.24"),
            _inv("mw_nginx_1_26", "Nginx", "1.26", "nginx", "nginx", "1.26"),
            _inv("mw_httpd_2_4", "Apache HTTP Server", "2.4", "apache", "http_server", "2.4"),
            _inv("mw_kafka_3_5", "Apache Kafka", "3.5", "apache", "kafka", "3.5"),
            _inv("mw_kafka_3_7", "Apache Kafka", "3.7", "apache", "kafka", "3.7"),
            _inv("mw_kafka_4", "Apache Kafka", "4", "apache", "kafka", "4"),
            _inv("mw_rabbitmq_3_12", "RabbitMQ", "3.12", "vmware", "rabbitmq", "3.12"),
            _inv("mw_rabbitmq_4", "RabbitMQ", "4", "vmware", "rabbitmq", "4"),
            _inv("mw_elasticsearch_8", "Elasticsearch", "8", "elastic", "elasticsearch", "8"),
            _inv("mw_elasticsearch_9", "Elasticsearch", "9", "elastic", "elasticsearch", "9"),
            _inv("mw_activemq_5", "Apache ActiveMQ", "5", "apache", "activemq", "5"),
            _inv("mw_wildfly_31", "WildFly", "31", "redhat", "wildfly", "31"),
            _inv("mw_jetty_11", "Eclipse Jetty", "11", "eclipse", "jetty", "11"),
            _inv("mw_jetty_12", "Eclipse Jetty", "12", "eclipse", "jetty", "12"),
            _inv("mw_undertow_2", "Undertow", "2", "redhat", "undertow", "2"),
            _inv("mw_iis_10", "IIS", "10", "microsoft", "internet_information_services", "10"),
            _inv("mw_traefik_3", "Traefik", "3", "traefik", "traefik", "3"),
        ],
    },
    "os": {
        "name": "OS",
        "description": "서버·클라이언트 OS. 상위: Windows Server, RHEL, Ubuntu LTS.",
        "codes": [
            _inv("os_windows_server_2019", "Windows Server", "2019", "microsoft", "windows_server", "2019"),
            _inv("os_windows_server_2022", "Windows Server", "2022", "microsoft", "windows_server", "2022"),
            _inv("os_windows_server_2025", "Windows Server", "2025", "microsoft", "windows_server", "2025"),
            _inv("os_rhel_7", "Red Hat Enterprise Linux", "7", "redhat", "enterprise_linux", "7"),
            _inv("os_rhel_8", "Red Hat Enterprise Linux", "8", "redhat", "enterprise_linux", "8"),
            _inv("os_rhel_9", "Red Hat Enterprise Linux", "9", "redhat", "enterprise_linux", "9"),
            _inv("os_ubuntu_20_04", "Ubuntu", "20.04", "canonical", "ubuntu_linux", "20.04"),
            _inv("os_ubuntu_22_04", "Ubuntu", "22.04", "canonical", "ubuntu_linux", "22.04"),
            _inv("os_ubuntu_24_04", "Ubuntu", "24.04", "canonical", "ubuntu_linux", "24.04"),
            _inv("os_amazon_linux_2", "Amazon Linux", "2", "amazon", "amazon_linux", "2"),
            _inv("os_amazon_linux_2023", "Amazon Linux", "2023", "amazon", "amazon_linux", "2023"),
            _inv("os_rocky_8", "Rocky Linux", "8", "rockylinux", "rocky_linux", "8"),
            _inv("os_rocky_9", "Rocky Linux", "9", "rockylinux", "rocky_linux", "9"),
            _inv("os_almalinux_8", "AlmaLinux", "8", "almalinux", "almalinux", "8"),
            _inv("os_almalinux_9", "AlmaLinux", "9", "almalinux", "almalinux", "9"),
            _inv("os_debian_11", "Debian", "11", "debian", "debian_linux", "11"),
            _inv("os_debian_12", "Debian", "12", "debian", "debian_linux", "12"),
            _inv("os_oracle_linux_8", "Oracle Linux", "8", "oracle", "linux", "8"),
            _inv("os_oracle_linux_9", "Oracle Linux", "9", "oracle", "linux", "9"),
            _inv("os_sles_15", "SUSE Linux Enterprise Server", "15", "suse", "linux_enterprise_server", "15"),
            _inv("os_aix_7", "IBM AIX", "7", "ibm", "aix", "7"),
            _inv("os_macos_14", "macOS", "14", "apple", "mac_os_x", "14"),
            _inv("os_macos_15", "macOS", "15", "apple", "mac_os_x", "15"),
        ],
    },
    "db": {
        "name": "DB",
        "description": "데이터베이스·캐시. 상위: PostgreSQL, Oracle Database, MySQL.",
        "codes": [
            _inv("db_postgresql_14", "PostgreSQL", "14", "postgresql", "postgresql", "14"),
            _inv("db_postgresql_15", "PostgreSQL", "15", "postgresql", "postgresql", "15"),
            _inv("db_postgresql_16", "PostgreSQL", "16", "postgresql", "postgresql", "16"),
            _inv("db_postgresql_17", "PostgreSQL", "17", "postgresql", "postgresql", "17"),
            _inv("db_oracle_12c", "Oracle Database", "12c", "oracle", "database_server", "12"),
            _inv("db_oracle_19c", "Oracle Database", "19c", "oracle", "database_server", "19"),
            _inv("db_oracle_23ai", "Oracle Database", "23ai", "oracle", "database_server", "23"),
            _inv("db_mysql_5_7", "MySQL", "5.7", "oracle", "mysql", "5.7"),
            _inv("db_mysql_8_0", "MySQL", "8.0", "oracle", "mysql", "8.0"),
            _inv("db_mysql_8_4", "MySQL", "8.4", "oracle", "mysql", "8.4"),
            _inv("db_mariadb_10_11", "MariaDB", "10.11", "mariadb", "mariadb", "10.11"),
            _inv("db_mariadb_11_4", "MariaDB", "11.4", "mariadb", "mariadb", "11.4"),
            _inv("db_sqlserver_2019", "Microsoft SQL Server", "2019", "microsoft", "sql_server", "2019"),
            _inv("db_sqlserver_2022", "Microsoft SQL Server", "2022", "microsoft", "sql_server", "2022"),
            _inv("db_mongodb_6", "MongoDB", "6", "mongodb", "mongodb", "6"),
            _inv("db_mongodb_7", "MongoDB", "7", "mongodb", "mongodb", "7"),
            _inv("db_mongodb_8", "MongoDB", "8", "mongodb", "mongodb", "8"),
            _inv("db_redis_6", "Redis", "6", "redis", "redis", "6"),
            _inv("db_redis_7", "Redis", "7", "redis", "redis", "7"),
            _inv("db_redis_8", "Redis", "8", "redis", "redis", "8"),
            _inv("db_cassandra_4", "Apache Cassandra", "4", "apache", "cassandra", "4"),
            _inv("db_sqlite_3", "SQLite", "3", "sqlite", "sqlite", "3"),
            _inv("db_db2_11_5", "IBM Db2", "11.5", "ibm", "db2", "11.5"),
        ],
    },
}


class Command(BaseCommand):
    help = "Seed default CodeGroup/Code values"

    def handle(self, *args, **kwargs):
        seed_data = {
            "use_flag": {
                "name": "사용여부",
                "codes": [("Y", "사용"), ("N", "미사용")],
            },
            "devops_type": {
                "name": "개발/운영",
                "codes": [("DEV", "개발"), ("OPS", "운영"), ("BOTH", "개발/운영")],
            },
            "infra_type": {
                "name": "인프라 구분",
                "codes": [("ONPREM", "On-Prem"), ("AWS", "AWS"), ("OTHER", "기타")],
            },
            "network_zone": {
                "name": "네트워크 구분",
                "codes": [("DMZ", "DMZ"), ("SF", "Server Farm"), ("ETC", "기타")],
            },
            "platform_type": {
                "name": "플랫폼 구분",
                "codes": [("WEB", "WEB"), ("CS", "CS"), ("MOBILE", "MOBILE"), ("ETC", "기타")],
            },
            "person_role": {
                "name": "담당자 역할",
                "codes": [
                    ("customer_it", "고객사 IT 담당"),
                    ("sk_owner", "Infa 담당자(SK)"),
                    ("partner", "Appl. 운영자"),
                    ("developer", "개발담당"),
                    ("operator", "운영담당"),
                ],
            },
        }

        for index, (group_key, group_data) in enumerate(seed_data.items(), start=1):
            group, _ = CodeGroup.objects.update_or_create(
                key=group_key,
                defaults={
                    "name": group_data["name"],
                    "sort_order": index * 10,
                    "is_active": True,
                },
            )

            for code_index, (code, name) in enumerate(group_data["codes"], start=1):
                Code.objects.update_or_create(
                    group=group,
                    code=code,
                    defaults={
                        "name": name,
                        "sort_order": code_index * 10,
                        "is_active": True,
                        "related_code": None,
                    },
                )

        # 이전 시드의 component 분류/유형 그룹 제거 (7개 신규 그룹과 중복 개념 정리)
        CodeGroup.objects.filter(key__in=("component_category", "component_type")).delete()

        base_order = len(seed_data) * 10
        for gi, (group_key, group_data) in enumerate(PRODUCT_VERSION_GROUPS.items(), start=1):
            group, _ = CodeGroup.objects.update_or_create(
                key=group_key,
                defaults={
                    "name": group_data["name"],
                    "description": group_data.get(
                        "description",
                        "제품명 + 공백 + 버전 표기. CVE/CPE 매핑은 Code.extra.inventory 확장.",
                    ),
                    "sort_order": base_order + gi * 10,
                    "is_active": True,
                },
            )
            for ci, row in enumerate(group_data["codes"], start=1):
                code, name, extra = row
                Code.objects.update_or_create(
                    group=group,
                    code=code,
                    defaults={
                        "name": name,
                        "sort_order": ci * 10,
                        "is_active": True,
                        "related_code": None,
                        "extra": extra,
                    },
                )
            keep_codes = {row[0] for row in group_data["codes"]}
            Code.objects.filter(group=group).exclude(code__in=keep_codes).delete()

        self.stdout.write(self.style.SUCCESS("Code groups and codes created/updated"))

