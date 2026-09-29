CREATE INDEX ix_patent_document_id IF NOT EXISTS FOR (n:Patent) ON (n.document_id);
CREATE INDEX ix_patent_revision_id IF NOT EXISTS FOR (n:Patent) ON (n.revision_id);
CREATE INDEX ix_patent_publication_number IF NOT EXISTS FOR (n:Patent) ON (n.publication_number);
CREATE INDEX ix_work_document_id IF NOT EXISTS FOR (n:ScientificWork) ON (n.document_id);
CREATE INDEX ix_work_revision_id IF NOT EXISTS FOR (n:ScientificWork) ON (n.revision_id);
CREATE INDEX ix_work_openalex_id IF NOT EXISTS FOR (n:ScientificWork) ON (n.openalex_id);
CREATE INDEX ix_classification_scheme_code IF NOT EXISTS FOR (n:Classification) ON (n.scheme, n.code);
