CREATE TABLE IF NOT EXISTS shop (
    id SERIAL PRIMARY KEY,
    category TEXT,
    subcategory TEXT,
    name TEXT,
    description TEXT,
    photoid TEXT,
    count INTEGER,
    price INTEGER,
    onsell BOOLEAN,
    dateadded TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sendmessages (
    id SERIAL PRIMARY KEY,
    text TEXT,
    filetype VARCHAR(255),
    fileid TEXT,
    datesend TIMESTAMP DEFAULT NOW(),
    userswhom_id TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    username VARCHAR(255),
    shipp_adress TEXT,
    dateadded TIMESTAMP DEFAULT NOW(),
    lastonline TIMESTAMP
);

CREATE TABLE IF NOT EXISTS FAQ (
    id SERIAL PRIMARY KEY,
    quest TEXT,
    answer TEXT
);

CREATE TABLE IF NOT EXISTS basket (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    product_id INTEGER,
    count INTEGER,
    topay TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tgadmins (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    username VARCHAR(255),
    dateadded TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255),
    values TEXT,
    dateadded TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255),
    typedata VARCHAR(255),
    values TEXT,
    dateadded TIMESTAMP DEFAULT NOW()
);



