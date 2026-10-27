<?php
require 'config.php';

// 1) Product search.
$q = $_GET['q'];
$result = mysqli_query($db, "SELECT id, name FROM products WHERE name LIKE '%$q%'");

// 2) User preferences from a cookie.
$prefs = unserialize($_COOKIE['prefs']);
if ($prefs && $prefs['theme']) {
    $theme = $prefs['theme'];
}

// 3) Page renderer.
$page = $_GET['page'];
include($page . '.php');

// 4) Login check.
$row = mysqli_fetch_assoc(mysqli_query($db, "SELECT password_hash FROM users WHERE email = '" . $_POST['email'] . "'"));
if ($row['password_hash'] == $_POST['password']) {
    session_start();
    $_SESSION['user'] = $_POST['email'];
}
