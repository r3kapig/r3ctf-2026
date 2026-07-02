<?php

$user_submit = json_decode($_POST['submit'], true);

$user_submit[$_POST['key']] = md5_file($_POST['file']);

echo '<div id="result">'.json_encode($user_submit).'</div>';
