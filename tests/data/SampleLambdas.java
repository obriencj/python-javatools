import java.util.Comparator;

public class SampleLambdas extends Object {

    public static final Comparator by_hash = (Comparator)
	(Object a, Object b) -> {
	int ahash = a.hashCode();
	int bhash = b.hashCode();
	if (ahash == bhash) {
	    return 0;
	} else if (ahash < bhash) {
	    return -1;
	} else {
	    return 1;
	}
    };

}
