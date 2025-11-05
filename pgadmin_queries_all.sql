-- ============================================================================
-- PGADMIN4'TE ÇALIŞTIRMA İÇİN - Her iki sistem'in üyeliklerini kontrol et
-- ============================================================================

-- 1. CEMMAKSERVİS USERS (Orijinal Tablo)
-- Diğer Flask sistemi tarafından kullanılan tablo
SELECT 'CERMAKSERVIS' as sistem, * FROM users 
ORDER BY id;

-- 2. ENVANTERQR USERS (Yeni Tablo)
-- EnvanterQR sistemi tarafından kullanılan tablo
SELECT 'ENVANTERQR' as sistem, * FROM envanter_users 
ORDER BY id;

-- 3. KARŞILAŞTIRMA - İki tablo'daki tüm üyeleri yan yana gör
SELECT 
    u.id as users_id,
    u.username as users_username,
    u.full_name as users_fullname,
    u.role as users_role,
    eu.id as envanter_users_id,
    eu.username as envanter_users_username,
    eu.full_name as envanter_users_fullname,
    eu.role as envanter_users_role
FROM users u
FULL OUTER JOIN envanter_users eu ON u.id = eu.id
ORDER BY COALESCE(u.id, eu.id);

-- 4. CEMMAKSERVİS - Tüm kullanıcı detayları
SELECT 
    id,
    username,
    full_name,
    email,
    password_hash,
    role,
    created_at
FROM users
ORDER BY id DESC;

-- 5. ENVANTERQR - Tüm kullanıcı detayları (yeni tablo)
SELECT 
    id,
    username,
    full_name,
    email,
    password,
    password_hash,
    role,
    created_at
FROM envanter_users
ORDER BY id DESC;

-- 6. İSTATİSTİKLER
SELECT 
    'users (cermakservis)' as tablo,
    COUNT(*) as toplam_kullanıcı,
    COUNT(DISTINCT role) as farkli_roller
FROM users
UNION ALL
SELECT 
    'envanter_users (envanterqr)' as tablo,
    COUNT(*) as toplam_kullanıcı,
    COUNT(DISTINCT role) as farkli_roller
FROM envanter_users;

-- 7. TABLO KOLONLARI KIYASLA
SELECT 
    'users' as tablo,
    string_agg(column_name, ', ' ORDER BY ordinal_position) as kolonlar
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'users'
UNION ALL
SELECT 
    'envanter_users' as tablo,
    string_agg(column_name, ', ' ORDER BY ordinal_position) as kolonlar
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'envanter_users';

-- 8. DETAYLI TABLO YAPISI
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name IN ('users', 'envanter_users')
ORDER BY table_name, ordinal_position;

-- 9. CEMMAKSERVİS - Role'ye göre kullanıcılar
SELECT 
    role,
    COUNT(*) as adet,
    string_agg(username, ', ') as kullanıcılar
FROM users
GROUP BY role
ORDER BY adet DESC;

-- 10. ENVANTERQR - Role'ye göre kullanıcılar
SELECT 
    role,
    COUNT(*) as adet,
    string_agg(username, ', ') as kullanıcılar
FROM envanter_users
GROUP BY role
ORDER BY adet DESC;

-- 11. ID ÇAKIŞMA KONTROLÜ (aynı ID'ye sahip kullanıcılar var mı?)
SELECT 
    u.id,
    u.username as users_username,
    eu.username as envanter_users_username,
    CASE 
        WHEN u.username = eu.username THEN 'SAME USERNAME'
        ELSE 'DIFFERENT USERNAME'
    END as durum
FROM users u
INNER JOIN envanter_users eu ON u.id = eu.id;

-- 12. MIGRATION KONTROL - test1 kullanıcısı
SELECT 
    'cermakservis' as kaynak,
    username,
    full_name,
    password,
    password_hash,
    role,
    created_at
FROM users
WHERE username = 'test1'
UNION ALL
SELECT 
    'envanterqr' as kaynak,
    username,
    full_name,
    password,
    password_hash,
    role,
    created_at
FROM envanter_users
WHERE username = 'test1';

-- 13. YETKILENDIRME KONTROLÜ - admin kullanıcıları
SELECT 
    'cermakservis' as sistem,
    id,
    username,
    full_name,
    role
FROM users
WHERE LOWER(role) = 'admin'
UNION ALL
SELECT 
    'envanterqr' as sistem,
    id,
    username,
    full_name,
    role
FROM envanter_users
WHERE LOWER(role) = 'admin'
ORDER BY sistem, id;

-- 14. EMAIL ALANLARI (eğer users tablosunda kullanılıyorsa)
SELECT 
    'cermakservis' as sistem,
    COUNT(*) as toplam,
    COUNT(email) as email_adet,
    COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as email_dolu
FROM users
UNION ALL
SELECT 
    'envanterqr' as sistem,
    COUNT(*) as toplam,
    COUNT(email) as email_adet,
    COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as email_dolu
FROM envanter_users;

-- 15. FOREIGN KEY İLİŞKİLERİ KONTROL ET
SELECT 
    constraint_name,
    table_name,
    column_name,
    referenced_table_name,
    referenced_column_name
FROM (
    SELECT
        tc.constraint_name,
        kcu.table_name,
        kcu.column_name,
        ccu.table_name as referenced_table_name,
        ccu.column_name as referenced_column_name
    FROM information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
) fk
WHERE referenced_table_name IN ('users', 'envanter_users')
ORDER BY table_name, column_name;
