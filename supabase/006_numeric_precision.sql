SET search_path TO promptto;
ALTER TABLE traction_values ALTER COLUMN value TYPE NUMERIC(20,2) USING value::numeric(20,2);
ALTER TABLE reviews ALTER COLUMN quality TYPE DOUBLE PRECISION USING quality::double precision;
ALTER TABLE policy_assessments ALTER COLUMN quality TYPE DOUBLE PRECISION USING quality::double precision;
