#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FRAME_SIZE 1024
#define FRAME_NUM 20
#define PF32DATA_DIR "/home/ding/pf32/c++_sample_linux-1.5.23/PhotonForce/C++/raw.dat"
#define OUTPUT_FILE "cut.dat"

unsigned int databuffer[FRAME_NUM][FRAME_SIZE];

void Read_PF32data(const char* filename, unsigned int databuffer[FRAME_NUM][FRAME_SIZE])
{
    FILE* file = fopen(filename, "r+");
    if(file == NULL)
    {
        perror("open file error");
        exit(1);
    }

    char line_data[8000];
    int data_index = 0;

    FILE* output_file = fopen(OUTPUT_FILE, "w+");
    if(output_file == NULL)
    {
        perror("create output file error");
        exit(1);
    }

    while(fgets(line_data, sizeof(line_data), file) != NULL)
    {
        if(line_data[0] == 'F' && line_data[1] == 'r' && line_data[2] == 'a' && line_data[3] == 'm' && line_data[4] == 'e')
        {
            fgets(line_data, sizeof(line_data), file);

            int Data_Everyframe;
            int Seq_Everyframe = 0;
            char* Linedata_ptr = line_data;

            while(sscanf(Linedata_ptr, "%d", &Data_Everyframe) == 1)
            {
                databuffer[data_index][Seq_Everyframe] = Data_Everyframe;
                Seq_Everyframe++;

                fprintf(output_file, "%d ", Data_Everyframe);

                while(*Linedata_ptr != ' ' && *Linedata_ptr != '\0')
                {
                    Linedata_ptr++;
                }

                while(*Linedata_ptr == ' ')
                {
                    Linedata_ptr++;
                }
            }

            fprintf(output_file, "\n");
            data_index++;
        }
    }

    fclose(file);
    fclose(output_file);
}

void SaveToFile(unsigned int databuffer[FRAME_NUM][FRAME_SIZE], int start_frame, int end_frame, const char* filename)
{
    FILE* file = fopen(filename, "w+");
    if(file == NULL)
    {
        perror("create output file error");
        exit(1);
    }

    for(int i = start_frame; i < end_frame; i++)
    {
        for(int j = 0; j < FRAME_SIZE; j++)
        {
            fprintf(file, "%d ", databuffer[i][j]);
        }
        fprintf(file, "\n");
    }

    fclose(file);
}

int main()
{
    Read_PF32data(PF32DATA_DIR, databuffer);

    int frames_per_file = 10;
    int num_files = FRAME_NUM / frames_per_file;

    for(int i = 0; i < num_files; i++)
    {
        char filename[20];
        sprintf(filename, "cut_%d.dat", i+1);
        SaveToFile(databuffer, i * frames_per_file, (i + 1) * frames_per_file, filename);
    }

    return 0;
}
