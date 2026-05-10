//package com.farmwatch.service.auth;
//
//import lombok.RequiredArgsConstructor;
//import lombok.extern.slf4j.Slf4j;
//import org.springframework.beans.factory.annotation.Value;
//import org.springframework.security.crypto.password.PasswordEncoder;
//import org.springframework.stereotype.Service;
//
//import java.util.concurrent.atomic.AtomicReference;
//
//@Service
//@RequiredArgsConstructor
//@Slf4j
//public class AuthService {
//
//    private final JwtService jwtService;
//    private final PasswordEncoder passwordEncoder;
//
//    @Value("${farmwatch.auth.admin-password}")
//    private String initialAdminPassword;
//
//    // In-memory stored hashed password (persists while app runs)
//    // For production: store in DB or system_config table
//    private final AtomicReference<String> currentPasswordHash = new AtomicReference<>();
//
//    private String getPasswordHash() {
//        // Lazy init — hash the configured password on first use
//        if (currentPasswordHash.get() == null) {
//            currentPasswordHash.set(passwordEncoder.encode(initialAdminPassword));
//        }
//        return currentPasswordHash.get();
//    }
//
//    /**
//     * Authenticate with username "admin" and the current password.
//     * Returns a JWT token if successful, throws if not.
//     */
//    public String login(String username, String password) {
//        if (!"admin".equals(username)) {
//            throw new IllegalArgumentException("Invalid credentials");
//        }
//        if (!passwordEncoder.matches(password, getPasswordHash())) {
//            throw new IllegalArgumentException("Invalid credentials");
//        }
//        log.info("Admin logged in successfully");
//        return jwtService.generateToken(username);
//    }
//
//    /**
//     * Change the admin password.
//     * Requires the current password to be correct.
//     */
//    public void changePassword(String currentPassword, String newPassword) {
//        if (!passwordEncoder.matches(currentPassword, getPasswordHash())) {
//            throw new IllegalArgumentException("Current password is incorrect");
//        }
//        if (newPassword == null || newPassword.length() < 6) {
//            throw new IllegalArgumentException("New password must be at least 6 characters");
//        }
//        currentPasswordHash.set(passwordEncoder.encode(newPassword));
//        log.info("Admin password changed successfully");
//    }
//}
package com.farmwatch.service.auth;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.util.concurrent.atomic.AtomicReference;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuthService {

    private final JwtService jwtService;
    private final PasswordEncoder passwordEncoder;

    @Value("${farmwatch.auth.admin-password}")
    private String initialAdminPassword;

    private final AtomicReference<String> currentPasswordHash = new AtomicReference<>();

    // Called after @Value injection is complete
    @PostConstruct
    public void init() {
        currentPasswordHash.set(passwordEncoder.encode(initialAdminPassword));
        log.info("AuthService initialized — admin password hash set");
    }

    public String login(String username, String password) {
        log.info("Login attempt for username: '{}'", username);

        if (!"admin".equals(username)) {
            log.warn("Login failed — unknown username: '{}'", username);
            throw new IllegalArgumentException("Invalid credentials");
        }

        boolean matches = passwordEncoder.matches(password, currentPasswordHash.get());
        log.info("Password match result: {}", matches);

        if (!matches) {
            throw new IllegalArgumentException("Invalid credentials");
        }

        log.info("Login successful for: {}", username);
        return jwtService.generateToken(username);
    }
//public String login(String username, String password) {
//
//    System.out.println("USERNAME RECEIVED: [" + username + "]");
//    System.out.println("PASSWORD RECEIVED: [" + password + "]");
//
//    if (!"admin".equals(username)) {
//        System.out.println("USERNAME WRONG");
//        throw new IllegalArgumentException("Invalid credentials");
//    }
//
//    String storedHash = currentPasswordHash.get(); // ✅ FIX HERE
//    System.out.println("HASH USED: " + storedHash);
//
//    if (!passwordEncoder.matches(password, storedHash)) {
//        System.out.println("PASSWORD DOES NOT MATCH");
//        throw new IllegalArgumentException("Invalid credentials");
//    }
//
//    System.out.println("LOGIN SUCCESS");
//
//    return jwtService.generateToken(username);
//}

    public void changePassword(String currentPassword, String newPassword) {
        if (!passwordEncoder.matches(currentPassword, currentPasswordHash.get())) {
            throw new IllegalArgumentException("Current password is incorrect");
        }
        if (newPassword == null || newPassword.length() < 6) {
            throw new IllegalArgumentException("New password must be at least 6 characters");
        }
        currentPasswordHash.set(passwordEncoder.encode(newPassword));
        log.info("Admin password changed successfully");
    }
}