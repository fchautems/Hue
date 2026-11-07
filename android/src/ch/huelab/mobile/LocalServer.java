package ch.huelab.mobile;

import java.net.URI;

final class LocalServer {
    static String normalize(String input) {
        String address = input.trim();
        if (!address.contains("://")) address = "http://" + address;
        try {
            URI uri = URI.create(address);
            String host = uri.getHost();
            if (!"http".equals(uri.getScheme()) || host == null || uri.getUserInfo() != null
                    || uri.getQuery() != null || uri.getFragment() != null
                    || !uri.getPath().matches("/?")) return null;
            String[] parts = host.split("\\.");
            if (parts.length != 4) return null;
            int[] octets = new int[4];
            for (int index = 0; index < parts.length; index++) {
                if (!parts[index].matches("0|[1-9][0-9]{0,2}")) return null;
                octets[index] = Integer.parseInt(parts[index]);
                if (octets[index] > 255) return null;
            }
            int first = octets[0], second = octets[1];
            boolean local = first == 10 || (first == 172 && second >= 16 && second <= 31)
                    || (first == 192 && second == 168);
            int port = uri.getPort() == -1 ? 8765 : uri.getPort();
            if (!local || port < 1 || port > 65535) return null;
            return "http://" + host + ":" + port;
        } catch (IllegalArgumentException invalid) {
            return null;
        }
    }

    private LocalServer() {}
}
