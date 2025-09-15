CREATE TABLE health_check (
  id INT PRIMARY KEY AUTO_INCREMENT,
  message VARCHAR(255)
);
INSERT INTO health_check (message) VALUES ('ok');