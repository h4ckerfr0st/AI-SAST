<?php
// Vulnerable.php
class Vulnerable {
    private $db;

    public function __construct() {
        $this->db = new mysqli("127.0.0.1", "root", "", "testdb");
    }

    public function handleRequest() {
        $name = isset($_GET['nome']) ? $_GET['nome'] : '';
        $id   = isset($_GET['pk']) ? $_GET['pk'] : '';

        // XSS: echoing user input directly into HTML
        echo "<h1>Welcome, " . $name . "</h1>";

        // SQLi: building query via string concatenation
        $query = "SELECT * FROM accounts WHERE id = " . $id . " LIMIT 1";
        $res = $this->db->query($query);

        if ($res) {
            while ($row = $res->fetch_assoc()) {
                echo "<p>User: " . $row['username'] . "</p>";
            }
        } else {
            echo "<p>No user found.</p>";
        }
    }
}

$app = new Vulnerable();
$app->handleRequest();
