-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL DEFAULT 'pdf',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    extracted_text TEXT,
    anonymized_text TEXT,
    vector_embedding vector(384), -- 384-dimensional embeddings
    metadata JSONB DEFAULT '{}',
    processing_task_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document shares table for access control
CREATE TABLE IF NOT EXISTS document_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    shared_with_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permissions TEXT[] NOT NULL DEFAULT '{}',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(document_id, shared_with_user_id)
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document processing tasks table
CREATE TABLE IF NOT EXISTS document_processing_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_owner_id ON documents(owner_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_document_shares_document_id ON document_shares(document_id);
CREATE INDEX IF NOT EXISTS idx_document_shares_shared_with_user_id ON document_shares(shared_with_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_document_processing_tasks_document_id ON document_processing_tasks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_processing_tasks_status ON document_processing_tasks(status);

-- Create vector index for similarity search
CREATE INDEX IF NOT EXISTS idx_documents_vector_embedding ON documents USING ivfflat (vector_embedding vector_cosine_ops) WITH (lists = 100);

-- Create full-text search index
CREATE INDEX IF NOT EXISTS idx_documents_text_search ON documents USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '') || ' ' || COALESCE(extracted_text, '')));

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_document_processing_tasks_updated_at BEFORE UPDATE ON document_processing_tasks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function for vector similarity search
CREATE OR REPLACE FUNCTION similarity_search(
    query_embedding vector(384),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id UUID,
    title VARCHAR(255),
    description TEXT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.title,
        documents.description,
        1 - (documents.vector_embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE documents.vector_embedding IS NOT NULL
    AND 1 - (documents.vector_embedding <=> query_embedding) > match_threshold
    ORDER BY documents.vector_embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create function to get accessible documents for a user
CREATE OR REPLACE FUNCTION get_accessible_documents(user_uuid UUID)
RETURNS TABLE (
    id UUID,
    title VARCHAR(255),
    description TEXT,
    tags TEXT[],
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        d.id,
        d.title,
        d.description,
        d.tags,
        d.status,
        d.created_at
    FROM documents d
    LEFT JOIN document_shares ds ON d.id = ds.document_id
    WHERE d.owner_id = user_uuid OR ds.shared_with_user_id = user_uuid;
END;
$$;

-- Create RLS (Row Level Security) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_processing_tasks ENABLE ROW LEVEL SECURITY;

-- Users policies
CREATE POLICY "Users can view their own profile" ON users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update their own profile" ON users FOR UPDATE USING (auth.uid() = id);

-- Documents policies
CREATE POLICY "Users can view their own documents" ON documents FOR SELECT USING (owner_id = auth.uid());
CREATE POLICY "Users can view shared documents" ON documents FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM document_shares
        WHERE document_id = documents.id
        AND shared_with_user_id = auth.uid()
    )
);
CREATE POLICY "Users can insert their own documents" ON documents FOR INSERT WITH CHECK (owner_id = auth.uid());
CREATE POLICY "Users can update their own documents" ON documents FOR UPDATE USING (owner_id = auth.uid());
CREATE POLICY "Users can delete their own documents" ON documents FOR DELETE USING (owner_id = auth.uid());

-- Document shares policies
CREATE POLICY "Users can view document shares they created" ON document_shares FOR SELECT USING (created_by = auth.uid());
CREATE POLICY "Users can view document shares they are part of" ON document_shares FOR SELECT USING (shared_with_user_id = auth.uid());
CREATE POLICY "Users can insert document shares" ON document_shares FOR INSERT WITH CHECK (created_by = auth.uid());
CREATE POLICY "Users can update document shares they created" ON document_shares FOR UPDATE USING (created_by = auth.uid());
CREATE POLICY "Users can delete document shares they created" ON document_shares FOR DELETE USING (created_by = auth.uid());

-- Audit logs policies
CREATE POLICY "Users can view their own audit logs" ON audit_logs FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "System can insert audit logs" ON audit_logs FOR INSERT WITH CHECK (true);

-- Document processing tasks policies
CREATE POLICY "Users can view tasks for their documents" ON document_processing_tasks FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM documents
        WHERE documents.id = document_processing_tasks.document_id
        AND documents.owner_id = auth.uid()
    )
);
CREATE POLICY "System can insert processing tasks" ON document_processing_tasks FOR INSERT WITH CHECK (true);
CREATE POLICY "System can update processing tasks" ON document_processing_tasks FOR UPDATE WITH CHECK (true);