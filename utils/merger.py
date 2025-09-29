def merge_transcripts(transcripts, merges=6, overlaps=3):
    """
    Merge transcripts into chunks of `merges` items with overlap of `overlaps`.

    Args:
        transcripts (list[dict]): Each dict has {'timestamp': (start, end), 'text': str}
        n (int): Number of transcript items per merged chunk.
        m (int): Overlap count between consecutive chunks.

    Returns:
        list[dict]: Merged transcript chunks with combined timestamps and text.
    """
    merged = []
    i = 0
    while i < len(transcripts):
        chunk = transcripts[i:i+merges]
        if not chunk:
            break

        # Get merged timestamp
        start_time = chunk[0]['timestamp'][0]
        end_time = chunk[-1]['timestamp'][1]

        # Merge texts
        text = " ".join(c['text'] for c in chunk)

        merged.append({
            "timestamp": (start_time, end_time),
            "text": text
        })

        # Move index forward (merges - overlaps ensures overlap)
        i += (merges - overlaps)
        if i <= 0:  # safety check (avoid infinite loop if overlaps >= merges)
            i = len(transcripts)

    return merged


# text = [{'timestamp': (0.0, 2.0), 'text': ' In this presentation, we will try to understand'}, {'timestamp': (2.0, 4.0), 'text': ' what are wild pointers.'}, {'timestamp': (4.0, 6.0), 'text': " So, let's get started."}, {'timestamp': (6.0, 8.0), 'text': ' Wild pointers are also'}, {'timestamp': (8.0, 10.0), 'text': ' known as uninitialized pointers.'}, {'timestamp': (10.0, 12.0), 'text': ' Let me tell you, they are the pointers'}, {'timestamp': (12.0, 14.0), 'text': ' which are uninitialized, okay.'}, {'timestamp': (14.0, 18.0), 'text': ' So, these pointers usually point to some arbitrary memory location'}, {'timestamp': (18.0, 21.0), 'text': ' and may cause a program to crash or misbehave.'}, {'timestamp': (21.0, 28.84), 'text': " Obviously, they may point to some memory location which we even don't know, right. They definitely do not contain the address of some valid memory location, right. So, it may cause a program to crash or misbehave. Obviously, they may point to some memory location which we even don't know, right? They definitely do not contain the address of some valid memory location,"}, {'timestamp': (28.84, 33.66), 'text': ' right? So, it may cause a program to crash or misbehave. For example, here in this case,'}, {'timestamp': (33.66, 36.0), 'text': ' this pointer has not been initialized yet.'}, {'timestamp': (36.0, 38.0), 'text': ' And here we are trying to dereference'}, {'timestamp': (38.0, 40.0), 'text': ' this pointer. This means that'}, {'timestamp': (40.0, 42.0), 'text': ' we are trying to access the location'}, {'timestamp': (42.0, 44.0), 'text': ' pointed by this pointer. And we are also'}, {'timestamp': (44.0, 46.0), 'text': ' storing this value within that location.'}, {'timestamp': (46.0, 48.0), 'text': ' Obviously, this may cause the program'}, {'timestamp': (48.0, 50.0), 'text': ' to crash. It may even cause segmentation'}, {'timestamp': (50.0, 52.0), 'text': ' fault. We are trying to write into'}, {'timestamp': (52.0, 54.0), 'text': ' the memory which is an illegal memory.'}, {'timestamp': (54.0, 59.0), 'text': ' Basically, this pointer may contain the address of some illegal memory location.'}, {'timestamp': (59.0, 62.0), 'text': ' So, that is why this pointer is a wild pointer.'}, {'timestamp': (62.0, 66.0), 'text': ' It wildly behaves and may cause a program to crash or misbehave.'}, {'timestamp': (66.0, 68.0), 'text': ' So, this is a wild pointer'}, {'timestamp': (68.0, 70.0), 'text': ' without any doubt.'}, {'timestamp': (70.0, 72.0), 'text': ' Now, how to avoid'}, {'timestamp': (72.0, 74.0), 'text': ' wild pointers? What are the'}, {'timestamp': (74.0, 76.0), 'text': ' best practices to avoid wild pointers? The are the best practices to avoid wild pointers?'}, {'timestamp': (76.0, 81.0), 'text': ' The best practice is to initialize them with the address of a known variable.'}, {'timestamp': (81.0, 85.0), 'text': ' Here in this case, you can clearly see that pointer has been initialized'}, {'timestamp': (85.0, 87.0), 'text': ' with the address of this variable var.'}, {'timestamp': (87.0, 89.0), 'text': ' So, it is clear that this'}, {'timestamp': (89.0, 91.0), 'text': ' will no more be a wild pointer.'}, {'timestamp': (91.0, 94.0), 'text': ' It contains the address of a variable.'}, {'timestamp': (94.0, 96.0), 'text': ' There is no problem with this.'}, {'timestamp': (96.0, 100.56), 'text': ' Second is, that we should explicitly allocate the memory and put the values in the allocated'}, {'timestamp': (100.56, 106.36), 'text': ' memory. Here in this example, you can clearly see that we are allocating the memory using malloc.'}, {'timestamp': (106.36, 108.24), 'text': ' This is also a legal step.'}, {'timestamp': (108.24, 111.96), 'text': ' Here we are initializing this pointer with the address of the first byte of the memory'}, {'timestamp': (111.96, 113.86), 'text': ' allocated by this function.'}, {'timestamp': (113.86, 116.88), 'text': ' And obviously, we can access that location and put some values within them. This is fine. Either you should assign the address of the first byte of the memory allocated by this function. And obviously, we can access that location and put some values within them.'}, {'timestamp': (116.88, 118.0), 'text': ' This is fine.'}, {'timestamp': (118.0, 121.68), 'text': ' Either you should assign the address of some variable or some object'}, {'timestamp': (121.68, 125.0), 'text': ' or explicitly allocate the memory and put the values in'}, {'timestamp': (125.0, 126.68), 'text': ' the allocated memory.'}, {'timestamp': (126.68, 131.06), 'text': ' These two steps are fine to avoid wild pointers.'}, {'timestamp': (131.06, 133.04), 'text': ' Okay friends, this is it for now.'}, {'timestamp': (133.04, 145.4), 'text': ' Thank you for watching this presentation.'}]
# print(merge_transcripts(text, 5, 2))