from zilli.privacy.policy import (CLASS_LEVEL, CloudProvider, DataClass,
                                  DataGovernancePolicy, PolicyStore)


class TestDataGovernancePolicy:
    def test_public_allows_only_public(self):
        p = DataGovernancePolicy(max_allowed_class=DataClass.PUBLIC)
        assert p.allows_cloud_for(DataClass.PUBLIC) is True
        assert p.allows_cloud_for(DataClass.INTERNAL) is False

    def test_internal_allows_public_and_internal(self):
        p = DataGovernancePolicy(max_allowed_class=DataClass.INTERNAL)
        assert p.allows_cloud_for(DataClass.PUBLIC) is True
        assert p.allows_cloud_for(DataClass.INTERNAL) is True
        assert p.allows_cloud_for(DataClass.CONFIDENTIAL) is False

    def test_confidential_allows_up_to_confidential(self):
        p = DataGovernancePolicy(max_allowed_class=DataClass.CONFIDENTIAL)
        assert p.allows_cloud_for(DataClass.CONFIDENTIAL) is True
        assert p.allows_cloud_for(DataClass.RESTRICTED) is False

    def test_restricted_allows_up_to_restricted(self):
        p = DataGovernancePolicy(max_allowed_class=DataClass.RESTRICTED)
        assert p.allows_cloud_for(DataClass.RESTRICTED) is True
        assert p.allows_cloud_for(DataClass.REGULATED) is False

    def test_regulated_allows_nothing(self):
        p = DataGovernancePolicy(max_allowed_class=DataClass.REGULATED)
        assert p.allows_cloud_for(DataClass.REGULATED) is False

    def test_max_class_can_use_cloud(self):
        for cls in [DataClass.PUBLIC, DataClass.INTERNAL,
                    DataClass.CONFIDENTIAL, DataClass.RESTRICTED]:
            p = DataGovernancePolicy(max_allowed_class=cls)
            assert p.max_class_can_use_cloud() == cls

    def test_class_level_ordering(self):
        assert CLASS_LEVEL[DataClass.PUBLIC] < CLASS_LEVEL[DataClass.INTERNAL]
        assert CLASS_LEVEL[DataClass.INTERNAL] < CLASS_LEVEL[DataClass.CONFIDENTIAL]
        assert CLASS_LEVEL[DataClass.CONFIDENTIAL] < CLASS_LEVEL[DataClass.RESTRICTED]
        assert CLASS_LEVEL[DataClass.RESTRICTED] < CLASS_LEVEL[DataClass.REGULATED]


class TestPolicyStore:
    def test_get_default_policy(self):
        store = PolicyStore()
        p = store.get("unknown-tenant")
        assert p.tenant_id == "unknown-tenant"
        assert p.max_allowed_class == DataClass.CONFIDENTIAL

    def test_set_and_get(self):
        store = PolicyStore()
        custom = DataGovernancePolicy(tenant_id="acme",
                                      max_allowed_class=DataClass.PUBLIC)
        store.set("acme", custom)
        assert store.get("acme").max_allowed_class == DataClass.PUBLIC
        assert "acme" in store.list_tenants()

    def test_persistence_roundtrip(self, tmp_path):
        path = str(tmp_path / "policies.json")
        store = PolicyStore(path=path)
        store.set("acme", DataGovernancePolicy(
            tenant_id="acme",
            max_allowed_class=DataClass.RESTRICTED,
            allowed_cloud_providers=[CloudProvider.GOOGLE],
            require_consent=True,
            retention_days=30,
        ))

        store2 = PolicyStore(path=path)
        p = store2.get("acme")
        assert p.max_allowed_class == DataClass.RESTRICTED
        assert p.allowed_cloud_providers == [CloudProvider.GOOGLE]
        assert p.require_consent is True
        assert p.retention_days == 30

    def test_load_existing_file(self, tmp_path):
        import json
        path = tmp_path / "policies.json"
        path.write_text(json.dumps({
            "t1": {"tenant_id": "t1", "max_allowed_class": "public",
                   "allowed_cloud_providers": ["openai"]},
        }))
        store = PolicyStore(path=str(path))
        assert store.get("t1").max_allowed_class == DataClass.PUBLIC
