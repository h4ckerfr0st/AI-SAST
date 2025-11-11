package com.example.vuln;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.MediaType;
import java.sql.*;
import java.util.*;

@RestController
public class VulnerableController {

    @GetMapping(value="/vuln", produces = MediaType.TEXT_HTML_VALUE)
    public String vuln(@RequestParam(required=false, defaultValue="guest") String name,
                       @RequestParam(required=false, defaultValue="0") String id) {

        StringBuilder sb = new StringBuilder();
        sb.append("<html><body>");
        sb.append("<h1>Hello, ").append(name).append("</h1>");

        Connection conn = null;
        Statement stmt = null;
        try {
            conn = DriverManager.getConnection("jdbc:h2:mem:testdb", "sa", "");
            stmt = conn.createStatement();
            stmt.execute("CREATE TABLE IF NOT EXISTS users(id INT PRIMARY KEY, username VARCHAR(255))");
            stmt.execute("MERGE INTO users(id, username) KEY(id) VALUES(1,'alice')");

            String query = "SELECT username FROM users WHERE id = " + id;
            ResultSet rs = stmt.executeQuery(query);
            while (rs.next()) {
                sb.append("<p>User: ").append(rs.getString("username")).append("</p>");
            }
        } catch (SQLException e) {
            sb.append("<p>Error: ").append(e.getMessage()).append("</p>");
        } finally {
            try { if (stmt!=null) stmt.close(); } catch(Exception e){}
            try { if (conn!=null) conn.close(); } catch(Exception e){}
        }

        sb.append("</body></html>");
        return sb.toString();
    }
}
