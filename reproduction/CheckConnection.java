import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

/** Environment check only: read data counts; never run DProvDB workloads. */
class CheckConnection {
    public static void main(String[] args) throws Exception {
        Class.forName("org.postgresql.Driver");
        String[][] checks = {
            {"adult", "adult", "45222"},
            {"adult_upstream", "adult", "32561"},
            {"tpch", "orders", "1500000"},
            {"tpch", "lineitem", "6001215"}
        };
        for (String[] check : checks) {
            try (Connection db = DriverManager.getConnection(
                    "jdbc:postgresql://localhost:5432/" + check[0], "link", "12345");
                 Statement query = db.createStatement()) {
                query.setQueryTimeout(60);
                try (ResultSet result = query.executeQuery("SELECT count(*) FROM " + check[1])) {
                    result.next();
                    long count = result.getLong(1);
                    if (count != Long.parseLong(check[2])) {
                        throw new IllegalStateException(check[0] + "." + check[1] + ": " + count);
                    }
                    java.lang.System.out.println(check[0] + "." + check[1] + " = " + count + " OK");
                }
            }
        }
    }
}
