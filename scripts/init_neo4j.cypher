// Document ラベルを持つノードの id 属性をuniqueに。
CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
