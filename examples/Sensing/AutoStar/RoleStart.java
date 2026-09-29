import net.tinyos.message.MoteIF;
import net.tinyos.packet.BuildSource;
import net.tinyos.packet.PhoenixSource;
import net.tinyos.util.PrintStreamMessenger;

/** Tell the USB-connected mote to become the parent of the radio star. */
public class RoleStart {
  public static void main(String[] args) throws Exception {
    if (args.length != 1) {
      System.err.println("Usage: java RoleStart serial@/dev/ttyUSB0:telosb");
      System.exit(2);
    }
    PhoenixSource source = BuildSource.makePhoenix(args[0], PrintStreamMessenger.err);
    MoteIF mote = new MoteIF(source);
    RoleStartMsg message = new RoleStartMsg();
    message.set_start((short) 1);
    for (int attempt = 0; attempt < 3; attempt++) {
      mote.send(MoteIF.TOS_BCAST_ADDR, message);
      Thread.sleep(300);
    }
    Thread.sleep(600);
    System.out.println("Parent activation sent to " + args[0]);
    System.exit(0);
  }
}
