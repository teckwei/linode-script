package com.example;
import okhttp3.*;

public class LinodeAccessKeyCreator {
    private static final String API_URL = "https://api.linode.com/v4/object-storage/keys";
    private static final String TOKEN = ""; // Linode API Token

    public static void main(String[] args) {
        // Set up the OkHttp client
        OkHttpClient client = new OkHttpClient();

        // Define the JSON body for the request
        String jsonBody = """
            {
                "bucket_access": [
                    {
                        "bucket_name": "testing-bucket-project",
                        "permissions": "read_write",
                        "region": "jp-osa"
                    }
                ],
                "label": "test-tw-3",
                "regions": ["jp-osa","us-iad"]
            }
        """;

        // Build the POST request
        RequestBody body = RequestBody.create(
                jsonBody,
                MediaType.parse("application/json")
        );

        Request request = new Request.Builder()
                .url(API_URL)
                .post(body)
                .addHeader("Authorization", "Bearer " + TOKEN)
                .addHeader("accept", "application/json")
                .addHeader("content-type", "application/json")
                .build();

        // Execute the request and handle the response
        try (Response response = client.newCall(request).execute()) {
            if (response.isSuccessful()) {
                // Parse and print the response
                String responseBody = response.body().string();
                System.out.println("Access Key Created: " + responseBody);
            } else {
                System.err.println("Error: " + response.code() + " " + response.message());
                System.err.println(response.body().string());
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}