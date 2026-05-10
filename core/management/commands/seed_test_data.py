from datetime import date

from django.core.management.base import BaseCommand

from core.models import Code
from masters.models import (
    AttributeCode,
    Certificate,
    Component,
    ConfigurationMaster,
    ConfigurationAttribute,
    ConfigurationComponentMapping,
    PersonMaster,
    ServiceAttribute,
    ServiceConfigurationMapping,
    ServiceMaster,
    ServicePersonMapping,
)
from masters.service_person_grid import ensure_service_person_attribute_codes


def c(group_key, code):
    return Code.objects.filter(group__key=group_key, code=code).first()


class Command(BaseCommand):
    help = "재정리된 내부 테이블 테스트 데이터 생성"

    def handle(self, *args, **kwargs):
        self.stdout.write("기존 마스터/매핑 테스트 데이터 정리 중...")
        Certificate.objects.all().delete()
        ConfigurationComponentMapping.objects.all().delete()
        ServiceConfigurationMapping.objects.all().delete()
        ServicePersonMapping.objects.all().delete()
        ConfigurationAttribute.objects.all().delete()
        ServiceAttribute.objects.all().delete()
        Component.objects.all().delete()
        ConfigurationMaster.objects.all().delete()
        PersonMaster.objects.all().delete()
        ServiceMaster.objects.all().delete()
        AttributeCode.objects.all().delete()

        svc = ServiceMaster.objects.create(
            name="ITAM 포털",
            category_code=c("service_category", "ERP"),
            status_code=c("service_status", "운영중"),
            build_type_code=c("build_type", "SI개발"),
            itgc_code=c("yn_flag", "예"),
            service_grade_code=c("service_grade", "A"),
            opened_at=date(2026, 5, 1),
            description="재정리 스키마 테스트 서비스",
            created_by="system",
            updated_by="system",
        )

        person = PersonMaster.objects.create(
            employee_no="I00001",
            name="홍길동",
            role_code=c("person_role", "DT_TEAM"),
            affiliation_code=c("affiliation", "DT팀"),
            company="SKC",
            phone="010-1111-2222",
            email="hong@sktest.local",
            external_email="hong@example.com",
            gender_code=c("gender", "남"),
            status_code=c("person_status", "투입"),
            deployed_at=date(2026, 5, 1),
        )

        cfg = ConfigurationMaster.objects.create(
            hostname="ITAM-WEB-01",
            server_type_code=c("config_type", "WEB"),
            operation_dev_code=c("operation_type", "OPS"),
            infra_type_code=c("infra_type", "AWS"),
            location_code=c("infra_location", "AWS"),
            network_zone_code=c("network_zone", "DMZ"),
            ip="10.0.0.10",
            port="443",
            url="https://itam.local",
            created_by="system",
            updated_by="system",
        )

        comp = Component.objects.create(
            component_type_code=c("component_type", "library"),
            product_name="Django",
            version="5.2",
            vendor_name="Django Software Foundation",
            cpe_name="cpe:2.3:a:djangoproject:django:5.2:*:*:*:*:*:*:*",
            eos_date=date(2028, 12, 31),
            eol_date=date(2029, 12, 31),
            support_status_code=c("support_status", "SUPPORTED"),
            created_by="system",
            updated_by="system",
        )

        ensure_service_person_attribute_codes()

        svc_attr_dt = AttributeCode.objects.get(pk="SVC_ATTR_PERSON_DT_TEAM")
        ServiceAttribute.objects.create(service=svc, attribute_code=svc_attr_dt, value=str(person.pk))

        cfg_attr = AttributeCode.objects.create(
            attribute_code="CFG_OWNER_DEPT",
            name="운영부서",
            data_type_code=c("data_type", "STRING"),
            required_code=c("required_flag", "N"),
            searchable_code=c("searchable_flag", "Y"),
            target_code=c("attribute_target", "CONFIG"),
        )
        ConfigurationAttribute.objects.create(configuration=cfg, attribute_code=cfg_attr, value="클라우드운영셀")
        ServicePersonMapping.objects.create(
            service=svc,
            person=person,
            role_code=c("person_role", "DT_TEAM"),
            status_code=c("mapping_status", "ACTIVE"),
            started_at=date(2026, 5, 1),
        )
        ServiceConfigurationMapping.objects.create(
            service=svc,
            configuration=cfg,
            status_code=c("mapping_status", "ACTIVE"),
            started_at=date(2026, 5, 1),
        )
        ConfigurationComponentMapping.objects.create(
            configuration=cfg,
            component=comp,
            install_path="/opt/itam",
            use_yn_code=c("use_flag", "Y"),
            started_at=date(2026, 5, 1),
        )
        Certificate.objects.create(
            configuration=cfg,
            domain="itam.local",
            cert_format="PEM",
            expires_at=date(2027, 5, 1),
            issuer="LetsEncrypt",
            use_yn_code=c("use_flag", "Y"),
        )
        self.stdout.write(self.style.SUCCESS("재정리 테이블 테스트 데이터 생성 완료"))
