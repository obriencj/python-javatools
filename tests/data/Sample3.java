public class Sample3 extends Object {

    private Object data = null;
    private static Object lastData = null;

    public int[][] twoDimIntArray;

    private static synchronized void setLastData(Object data) {
	lastData = data;
    }

    private static synchronized Object getLastData() throws Exception {
	if (lastData == null) {
	    throw new Exception("no data");
	} else {
	    return lastData;
	}
    }

    public synchronized void setData(Object d) {
	data = d;
	setLastData(d);
    }

    public synchronized Object getData() throws Exception {
	if (data == null) {
	    data = getLastData();
	}
	return data;
    }

    public Object getData(Object defaultValue) {
	try {
	    return getData();
	} catch(Exception exc) {
	    return defaultValue;
	}
    }

}
