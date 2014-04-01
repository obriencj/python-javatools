public class Sample1 extends Object {

    public static final String DEFAULT_NAME = "Daphne";

    private String name = null;
    protected static String recent_name = null;

    public Sample1() {
	this(DEFAULT_NAME);
    }

    public Sample1(String name) {
	this.name = name;
	this.recent_name = name;
    }

    public String getName() {
	return name;
    }

    public static String getRecentName() {
	return recent_name;
    }

}
