-- Drop existing tables to start fresh
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS balances;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS holdings;
DROP TABLE IF EXISTS gamification;
DROP TABLE IF EXISTS achievements;

-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    participantId TEXT UNIQUE NOT NULL,
    researchGroup INTEGER NOT NULL,
    consentGiven BOOLEAN NOT NULL,
    consentTimestamp TIMESTAMP NOT NULL,
    consentIP TEXT NOT NULL,
    createdAt TIMESTAMP NOT NULL,
    lastLogin TIMESTAMP,
    role TEXT NOT NULL DEFAULT 'user'
);

-- Balances table
CREATE TABLE balances (
    user_id TEXT PRIMARY KEY,
    cashBalance REAL NOT NULL DEFAULT 10000.00,
    investedValue REAL NOT NULL DEFAULT 0.0,
    totalPortfolioValue REAL NOT NULL DEFAULT 10000.00,
    totalRealizedPnL REAL NOT NULL DEFAULT 0.0,
    totalUnrealizedPnL REAL NOT NULL DEFAULT 0.0,
    totalTrades INTEGER NOT NULL DEFAULT 0,
    winningTrades INTEGER NOT NULL DEFAULT 0,
    losingTrades INTEGER NOT NULL DEFAULT 0,
    lastCalculated TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Transactions table
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    transaction_type TEXT NOT NULL, -- 'BUY' or 'SELL'
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    total_value REAL NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    portfolioValueAfter REAL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Holdings table
CREATE TABLE holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL,
    average_price REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE (user_id, symbol)
);

-- Gamification stats table
CREATE TABLE gamification (
    user_id TEXT PRIMARY KEY,
    totalXP INTEGER NOT NULL DEFAULT 0,
    currentLevel INTEGER NOT NULL DEFAULT 1,
    xpToNextLevel INTEGER NOT NULL DEFAULT 100,
    loginStreak INTEGER NOT NULL DEFAULT 1,
    tradingStreak INTEGER NOT NULL DEFAULT 0,
    profitableStreak INTEGER NOT NULL DEFAULT 0,
    achievementsViewed INTEGER NOT NULL DEFAULT 0,
    leaderboardViews INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Achievements progress table
CREATE TABLE achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    achievement_id TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    completedAt TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- User Actions table for research logging
CREATE TABLE userActions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    session_id TEXT,
    action_type TEXT,
    action_category TEXT,
    action_data TEXT, -- Storing JSON as string
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
);