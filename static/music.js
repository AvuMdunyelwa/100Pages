const navbar = document.querySelector('.navbar');
const clearInput = document.querySelector('.close');
const formInput = document.querySelectorAll('input[type="text"], input[type="number"], textarea');
const likesForm = document.querySelectorAll('.likes-form');
const likeBtn = document.querySelectorAll('#like-btn');
const togglePassword = document.querySelector('#toggle-password');
const password = document.querySelector('#password-field');
const confirmPassword = document.querySelector('#confirm-password-toggle');
const passwordAgain = document.querySelector('#confirm-password');
const addImage = document.querySelector('#add-pp-input');
let liked = true;

window.onscroll = function () {
    if (window.scrollY > 50) {
        navbar.style.backgroundColor = '#0D1B2A';
    }else {
        navbar.style.background = 'none';
    }
};

setTimeout(function () {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach( function(alert) {
        let bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    });
}, 3000);

// unhide password

if (togglePassword) {
    togglePassword.addEventListener('click', function (e) {
        let type = password.getAttribute('type');

        if (type == 'password') {
            type = password.setAttribute('type', 'text');
            document.querySelector('.eye-icon img').src = 'static/eye-solid.svg';
        }else {
            document.querySelector('.eye-icon img').src = 'static/eye-closed.svg';
            type = password.setAttribute('type', 'password');
        }
    })
}

if (confirmPassword) {
    confirmPassword.addEventListener('click', function (e) {
        let type = passwordAgain.getAttribute('type');

        if (type == 'password') {
            type = passwordAgain.setAttribute('type', 'text');
            document.querySelector('.eye-icon-again img').src = 'static/eye-solid.svg';
        }else {
            document.querySelector('.eye-icon-again img').src = 'static/eye-closed.svg';
            type = passwordAgain.setAttribute('type', 'password');
        }
    })
}



// passing the song review data form & pre-filling the form for editing review
function getAttributes(element) {
    const songTitle = element.getAttribute("data-bs-title");
    const reviewId = element.getAttribute("data-bs-id");
    const songArtist = element.getAttribute("data-bs-artist");
    const reviewContent = element.getAttribute("data-bs-content");
    const rating = element.getAttribute("data-bs-rating");
    const coverImg = element.getAttribute("data-bs-img");
    const trackId = element.getAttribute("data-bs-trackid");
    return {songTitle, reviewId, songArtist, reviewContent, rating, coverImg, trackId};
}

document.addEventListener("show.bs.modal", function(event) {
    const modal = event.target;  // the modal being shown
    if (modal.id === "editReviewModal") {
        if (modal) {
            const clickedBtn = event.relatedTarget;
            const {songTitle, reviewId, songArtist, reviewContent, rating, coverImg} = getAttributes(clickedBtn);
            const modalTitle = modal.querySelector(".modal-title");
            modalTitle.textContent = `${songTitle} by ${songArtist}`;

            const form = modal.querySelector(".edit-review");
            form.querySelector("#content").value = reviewContent;
            form.querySelector("#rating").value = rating;
            form.querySelector("#reviewId").value = reviewId;

        }
    }else if (modal.id === "reviewSong") {
        if (modal) {
            const clickedBtn = event.relatedTarget 
            const {songTitle, trackId, coverImg, songArtist} = getAttributes(clickedBtn);
            console.log(trackId);
            const modalTitle = modal.querySelector(".modal-title");
            modalTitle.textContent = `${songTitle} by ${songArtist}`;

            const form = modal.querySelector(".modal-content");

            form.addEventListener('submit', function() {
                const btn = form.querySelector('#add-review');
                btn.disabled = true;
                btn.textContent = 'submitting..';
            })
            
            modal.querySelector("#trackId").value = trackId;
            form.querySelector("#trackTitle").value = songTitle;
            form.querySelector("#trackArtist").value = songArtist;
            form.querySelector("#trackImg").value = coverImg;
         }
    }
})

likesForm.forEach((form) => {
    form.addEventListener("submit", async function(event) {
        event.preventDefault();

        try {
            const response = await fetch("/likes", {
                method: "POST",
                body: new FormData(form)
            })

            if (response.redirected) {
                window.location.href = response.url;
                return;
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            };

            const data = await response.json();
            console.log("Response data:", data);

            const likeCountElement = form.querySelector('.like-count');
            likeCountElement.textContent = `${data.total_likes} likes`;

            const heartIcon = form.querySelector('#like-btn img');
            if (data.liked) {
                heartIcon.src = 'static/heart-solid.svg';
            } else {
                heartIcon.src = 'static/heart.svg';
            };

        } catch(error) {
            return error;
            alert("Please login to like a post");
        }
    });
})

// change button to colored button
likeBtn.forEach((btn) => {
    btn.addEventListener("click", function(event) {
        const heartIcon = btn.querySelector('#like-btn img');
        if (liked) {
            heartIcon.src = 'static/heart-solid.svg';
            liked = false;
            return;
        }else {
            heartIcon.src = 'static/heart.svg';
            liked = true;
        }
    });
})

const imageView = document.querySelector('#profile-picture');
console.log(imageView);
let selectedImage;
// add image and display to the profile picture
addImage.addEventListener('change', profilePic);


//adding the book cover
function profilePic(e) {
    selectedImage = e.target.files[0];
    console.log('image-selected: ', selectedImage);
    createObjectURL= URL.createObjectURL(selectedImage);
    imageView.style.backgroundImage = `url(${createObjectURL})`;
};