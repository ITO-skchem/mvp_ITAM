from django.core.management.base import BaseCommand

from core.models import Code, CodeGroup

# 제품명 + 메이저(또는 관례상 쓰는 메이저·마이너 라인)만: code 스네이케이스, name은 표기용
# 그룹당 16개, 자주 쓰이는 순(대략적 인기·엔터프라이즈 기준)
PRODUCT_VERSION_GROUPS = {
    "language": {
        "name": "Language",
        "codes": [
            ("java_17", "java 17"),
            ("java_11", "java 11"),
            ("python_3_12", "python 3.12"),
            ("python_3_11", "python 3.11"),
            ("nodejs_20", "nodejs 20"),
            ("nodejs_18", "nodejs 18"),
            ("typescript_5", "typescript 5"),
            ("kotlin_2", "kotlin 2"),
            ("go_1_23", "go 1.23"),
            ("csharp_12", "c# 12"),
            ("php_8", "php 8"),
            ("ruby_3", "ruby 3"),
            ("rust_1", "rust 1"),
            ("swift_5", "swift 5"),
            ("scala_3", "scala 3"),
            ("dart_3", "dart 3"),
        ],
    },
    "runtime": {
        "name": "Runtime",
        "codes": [
            ("jvm_17", "jvm 17"),
            ("jvm_11", "jvm 11"),
            ("nodejs_20", "nodejs 20"),
            ("nodejs_18", "nodejs 18"),
            ("dotnet_8", "dotnet 8"),
            ("dotnet_6", "dotnet 6"),
            ("python_3_12", "python 3.12"),
            ("python_3_11", "python 3.11"),
            ("graalvm_21", "graalvm 21"),
            ("temurin_17", "temurin 17"),
            ("corretto_17", "corretto 17"),
            ("wasmtime_18", "wasmtime 18"),
            ("v8_12", "v8 12"),
            ("deno_2", "deno 2"),
            ("bun_1", "bun 1"),
            ("quickjs_2024", "quickjs 2024"),
        ],
    },
    "framework": {
        "name": "Framework",
        "codes": [
            ("spring_boot_3", "spring boot 3"),
            ("spring_boot_2", "spring boot 2"),
            ("django_5", "django 5"),
            ("django_4", "django 4"),
            ("react_18", "react 18"),
            ("vue_3", "vue 3"),
            ("express_4", "express 4"),
            ("nestjs_11", "nestjs 11"),
            ("aspnet_core_9", "aspnet core 9"),
            ("rails_8", "rails 8"),
            ("laravel_11", "laravel 11"),
            ("flask_3", "flask 3"),
            ("nextjs_15", "nextjs 15"),
            ("svelte_5", "svelte 5"),
            ("quarkus_3", "quarkus 3"),
            ("spring_6", "spring 6"),
        ],
    },
    "library": {
        "name": "Library",
        "codes": [
            ("jackson_2", "jackson 2"),
            ("gson_2", "gson 2"),
            ("okhttp_4", "okhttp 4"),
            ("netty_4", "netty 4"),
            ("hibernate_6", "hibernate 6"),
            ("mybatis_3", "mybatis 3"),
            ("jquery_3", "jquery 3"),
            ("bootstrap_5", "bootstrap 5"),
            ("axios_1", "axios 1"),
            ("lodash_4", "lodash 4"),
            ("springdoc_2", "springdoc 2"),
            ("slf4j_2", "slf4j 2"),
            ("log4j2_2", "log4j2 2"),
            ("junit_5", "junit 5"),
            ("mockito_5", "mockito 5"),
            ("commons_lang_3", "commons lang 3"),
        ],
    },
    "middleware": {
        "name": "Middleware",
        "codes": [
            ("tomcat_9", "tomcat 9"),
            ("tomcat_10", "tomcat 10"),
            ("nginx_1", "nginx 1"),
            ("apache_2", "apache 2"),
            ("kafka_3", "kafka 3"),
            ("kafka_4", "kafka 4"),
            ("rabbitmq_3", "rabbitmq 3"),
            ("rabbitmq_4", "rabbitmq 4"),
            ("elasticsearch_8", "elasticsearch 8"),
            ("elasticsearch_9", "elasticsearch 9"),
            ("activemq_5", "activemq 5"),
            ("wildfly_30", "wildfly 30"),
            ("jetty_12", "jetty 12"),
            ("undertow_2", "undertow 2"),
            ("iis_10", "iis 10"),
            ("traefik_3", "traefik 3"),
        ],
    },
    "os": {
        "name": "OS",
        "codes": [
            ("windows_server_2022", "windows server 2022"),
            ("windows_server_2025", "windows server 2025"),
            ("rhel_9", "rhel 9"),
            ("rhel_8", "rhel 8"),
            ("ubuntu_24", "ubuntu 24"),
            ("ubuntu_22", "ubuntu 22"),
            ("amazon_linux_2023", "amazon linux 2023"),
            ("rocky_9", "rocky linux 9"),
            ("almalinux_9", "almalinux 9"),
            ("debian_12", "debian 12"),
            ("oracle_linux_8", "oracle linux 8"),
            ("centos_7", "centos 7"),
            ("macos_15", "macos 15"),
            ("suse_15", "suse 15"),
            ("aix_7", "aix 7"),
            ("solaris_11", "solaris 11"),
        ],
    },
    "db": {
        "name": "DB",
        "codes": [
            ("postgresql_17", "postgresql 17"),
            ("postgresql_16", "postgresql 16"),
            ("postgresql_15", "postgresql 15"),
            ("mysql_8", "mysql 8"),
            ("mariadb_11", "mariadb 11"),
            ("oracle_19", "oracle 19"),
            ("oracle_23", "oracle 23"),
            ("sqlserver_2022", "sqlserver 2022"),
            ("sqlserver_2019", "sqlserver 2019"),
            ("mongodb_8", "mongodb 8"),
            ("mongodb_7", "mongodb 7"),
            ("redis_7", "redis 7"),
            ("cassandra_4", "cassandra 4"),
            ("sqlite_3", "sqlite 3"),
            ("db2_12", "db2 12"),
            ("tidb_8", "tidb 8"),
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
                    "description": "제품명 + 메이저(또는 라인) 버전만 (예: tomcat 9, java 17)",
                    "sort_order": base_order + gi * 10,
                    "is_active": True,
                },
            )
            for ci, (code, name) in enumerate(group_data["codes"], start=1):
                Code.objects.update_or_create(
                    group=group,
                    code=code,
                    defaults={
                        "name": name,
                        "sort_order": ci * 10,
                        "is_active": True,
                        "related_code": None,
                    },
                )
            keep_codes = {c[0] for c in group_data["codes"]}
            Code.objects.filter(group=group).exclude(code__in=keep_codes).delete()

        self.stdout.write(self.style.SUCCESS("Code groups and codes created/updated"))
