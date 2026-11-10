public class NullTest {
    public static String getUserName(User user) {
        return user.getName();
    }

    public static void main(String[] args) {
        System.out.println(getUserName(null));
    }
}

class User {
    private String name;
    public User(String name) { this.name = name; }
    public String getName() { return name; }
}
