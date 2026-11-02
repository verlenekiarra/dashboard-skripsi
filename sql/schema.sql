CREATE DATABASE IF NOT EXISTS financial_risk
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE financial_risk;

CREATE TABLE IF NOT EXISTS App_Users (
    User_ID BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    Username VARCHAR(120) NOT NULL,
    Password_Hash VARCHAR(255) NOT NULL,
    Role ENUM('Administrator', 'Stakeholder', 'User') NOT NULL,
    Is_Active BOOLEAN NOT NULL DEFAULT TRUE,
    Created_At TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Updated_At TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (User_ID),
    UNIQUE KEY uq_app_users_username (Username),
    KEY idx_app_users_role (Role),
    KEY idx_app_users_active (Is_Active)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Stg_Financial_Statement (
    Staging_ID BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    Ticker_Code VARCHAR(20) NOT NULL,
    Statement_Name VARCHAR(64) NOT NULL,
    Item_Name VARCHAR(128) NOT NULL,
    Fiscal_Year YEAR NOT NULL,
    Value DECIMAL(20,2) NULL,
    Loaded_At TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (Staging_ID),
    UNIQUE KEY uq_staging_company_statement_item_year
        (Ticker_Code, Statement_Name, Item_Name, Fiscal_Year),
    KEY idx_staging_company_year (Ticker_Code, Fiscal_Year)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Dim_Company (
    Company_ID INT UNSIGNED NOT NULL AUTO_INCREMENT,
    Ticker_Code VARCHAR(20) NOT NULL,
    Company_Name VARCHAR(150) NOT NULL,
    Sector VARCHAR(100) NOT NULL,
    Sub_Sector VARCHAR(100) NULL,
    PRIMARY KEY (Company_ID),
    UNIQUE KEY uq_company_ticker (Ticker_Code),
    KEY idx_company_sector_subsector (Sector, Sub_Sector)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Dim_Time (
    Time_ID INT UNSIGNED NOT NULL,
    Fiscal_Year YEAR NOT NULL,
    PRIMARY KEY (Time_ID),
    UNIQUE KEY uq_time_fiscal_year (Fiscal_Year)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Fact_Risk_Analysis (
    Company_ID INT UNSIGNED NOT NULL,
    Time_ID INT UNSIGNED NOT NULL,
    Total_Revenue DECIMAL(20,2) NULL,
    Total_Receivables DECIMAL(20,2) NULL,
    Cost_of_Goods_Sold DECIMAL(20,2) NULL,
    Gross_Profit DECIMAL(20,2) NULL,
    Current_Assets DECIMAL(20,2) NULL,
    Net_PPE DECIMAL(20,2) NULL,
    Total_Assets DECIMAL(20,2) NULL,
    Depreciation_Expense DECIMAL(20,2) NULL,
    SGA_Expense DECIMAL(20,2) NULL,
    Total_Liabilities DECIMAL(20,2) NULL,
    Net_Income DECIMAL(20,2) NULL,
    Operating_Cash_Flow DECIMAL(20,2) NULL,
    DSRI DECIMAL(12,6) NULL,
    GMI DECIMAL(12,6) NULL,
    AQI DECIMAL(12,6) NULL,
    SGI DECIMAL(12,6) NULL,
    DEPI DECIMAL(12,6) NULL,
    SGAI DECIMAL(12,6) NULL,
    LVGI DECIMAL(12,6) NULL,
    TATA DECIMAL(12,6) NULL,
    M_Score DECIMAL(12,6) NULL,
    Status_178 VARCHAR(50) NOT NULL,
    Status_222 VARCHAR(50) NOT NULL,
    Anomaly_Label TINYINT NULL,
    Anomaly_Score DECIMAL(12,8) NULL,
    PRIMARY KEY (Company_ID, Time_ID),
    KEY idx_fact_time (Time_ID),
    KEY idx_fact_status_178 (Status_178),
    KEY idx_fact_status_222 (Status_222),
    KEY idx_fact_anomaly_label (Anomaly_Label),
    CONSTRAINT fk_fact_company
        FOREIGN KEY (Company_ID) REFERENCES Dim_Company (Company_ID)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk_fact_time
        FOREIGN KEY (Time_ID) REFERENCES Dim_Time (Time_ID)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB;
